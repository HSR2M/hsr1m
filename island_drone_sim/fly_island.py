"""실제 섬(월미도/강화도) DEM 위에서 드론이 산 정상을 한 바퀴 도는 시뮬레이션.

실행 예:
    python fly_island.py --island wolmido --gui                 # 창을 띄워 실시간(3배속)으로 보기
    python fly_island.py --island wolmido --agl 60 --radius 500 --speed 10 --video --video_fps 1
출력(results/):
    <island>_path.csv      시간, 위치, 목표, 지형고도, 지상고
    <island>_map.png       DEM 위에 비행경로(평면도) + 고도 프로파일
    <island>_flight.mp4/gif  추적 카메라 영상(--video)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import time

import numpy as np
import pybullet as p
from PIL import Image

from gym_pybullet_drones.utils.enums import DroneModel, Physics
from gym_pybullet_drones.utils.utils import sync

from follower import PathFollower, build_path
from island_aviary import IslandAviary
from terrain import ISLANDS, hypsometric_texture, load_dem, verify_terrain


def chase_frame(client, pos, vel, w=640, h=400):
    v = np.array(vel[:2]); v = v / (np.linalg.norm(v) + 1e-6)
    eye = [pos[0] - 2.5 * v[0], pos[1] - 2.5 * v[1], pos[2] + 1.0]
    view = p.computeViewMatrix(eye, [pos[0] + 40 * v[0], pos[1] + 40 * v[1], pos[2] - 8], [0, 0, 1], physicsClientId=client)
    proj = p.computeProjectionMatrixFOV(70, w / h, 0.5, 8000, physicsClientId=client)
    _, _, rgb, _, _ = p.getCameraImage(w, h, view, proj, renderer=p.ER_TINY_RENDERER, shadow=0,
                                       lightDirection=[1, 1, 2], physicsClientId=client)
    return np.reshape(rgb, (h, w, 4))[..., :3].astype(np.uint8)


def save_map(t, log, pts, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ex, ey = t.extent_m()
    fig, (a, b) = plt.subplots(2, 1, figsize=(9, 11), gridspec_kw=dict(height_ratios=[3, 1]))
    im = a.imshow(t.heights, origin="lower", extent=[-ex / 2, ex / 2, -ey / 2, ey / 2], cmap="terrain")
    a.plot(pts[:, 0], pts[:, 1], "w--", lw=1, label="planned path")
    a.plot(log["x"], log["y"], "r-", lw=1.5, label="flown")
    px, py, pz = t.peak(); a.plot(px, py, "k^", ms=8, label=f"peak {pz:.0f} m")
    a.set_title(f"{t.name}: DEM ({t.mpp:.1f} m/px) and drone track"); a.set_xlabel("east (m)"); a.set_ylabel("north (m)")
    a.legend(loc="upper right"); fig.colorbar(im, ax=a, label="elevation (m)")
    b.plot(log["t"], log["z"], "r-", label="drone altitude (MSL)")
    b.plot(log["t"], log["ground"], "k-", label="terrain below drone")
    b.fill_between(log["t"], 0, log["ground"], color="tan", alpha=0.5)
    b.set_xlabel("time (s)"); b.set_ylabel("m"); b.legend(); b.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_png, dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--island", default="wolmido", choices=list(ISLANDS))
    ap.add_argument("--agl", type=float, default=60.0, help="지형 위 비행고도(m)")
    ap.add_argument("--radius", type=float, default=500.0, help="정상 기준 선회 반경(m)")
    ap.add_argument("--speed", type=float, default=10.0, help="순항 속도(m/s)")
    ap.add_argument("--climb_speed", type=float, default=3.0, help="이륙 수직상승 속도(m/s); 빠르면 수평 전환 때 뒤집힌다")
    ap.add_argument("--max_err", type=float, default=0.6, help="PID에 넘기는 수평 위치오차 상한(m); 0.6 m = 0.24 N, 기울기 약 42도")
    ap.add_argument("--max_err_z", type=float, default=0.08, help="수직 위치오차 상한(m); 1.25 N/m 게인이라 0.1 m만 넘어도 추력이 역전")
    ap.add_argument("--accel", type=float, default=1.0, help="순항속도까지 가속도(m/s^2)")
    ap.add_argument("--max_lag", type=float, default=8.0, help="드론이 경로점에 이보다 뒤처지면 경로점이 기다린다(m)")
    ap.add_argument("--vel_tau", type=float, default=1.0, help="목표속도 저역통과 시정수(s); 경로가 꺾일 때 급변 방지")
    ap.add_argument("--max_vel_err", type=float, default=1.5, help="수평 속도오차 상한(m/s)")
    ap.add_argument("--max_vel_err_z", type=float, default=0.25, help="수직 속도오차 상한(m/s)")
    ap.add_argument("--ctrl_hz", type=int, default=48)
    ap.add_argument("--sim_hz", type=int, default=240)
    ap.add_argument("--video", action="store_true", help="추적 카메라 프레임을 저장해 mp4로 묶는다")
    ap.add_argument("--video_fps", type=float, default=1.0, help="시뮬 시간 기준 프레임 수/초 (소프트웨어 렌더라 프레임당 수 초 걸림)")
    ap.add_argument("--video_w", type=int, default=480, help="영상 가로 해상도(px), 세로는 5/8")
    ap.add_argument("--gui", action="store_true", help="PyBullet GUI 창에서 실시간으로 보기(카메라가 드론을 따라감)")
    ap.add_argument("--speedup", type=float, default=3.0, help="--gui일 때 실시간 대비 재생 배속")
    ap.add_argument("--out", default="results")
    ap.add_argument("--tiles", default="tiles")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    t = load_dem(args.island, args.tiles)
    tex = hypsometric_texture(t, os.path.join(args.out, f"{args.island}_tex.png"))
    ex, ey = t.extent_m(); px, py, pz = t.peak()
    print(f"[terrain] {args.island}: {t.cols}x{t.rows} px, {t.mpp:.1f} m/px, {ex/1000:.1f} x {ey/1000:.1f} km, peak {pz:.0f} m at ({px:.0f},{py:.0f})")

    pts, cum, climb_end = build_path(t, t.peak()[:2], args.radius, args.agl)
    start = pts[0]
    print(f"[path] {len(pts)} pts, length {cum[-1]:.0f} m, cruise z {pts[-1,2]:.0f} m, est. {cum[-1]/args.speed:.0f} s at {args.speed} m/s")

    env = IslandAviary(terrain=t, texture_path=tex, drone_model=DroneModel.CF2X, num_drones=1,
                       initial_xyzs=start.reshape(1, 3), initial_rpys=np.zeros((1, 3)), physics=Physics.PYB,
                       pyb_freq=args.sim_hz, ctrl_freq=args.ctrl_hz, gui=args.gui, obstacles=False, user_debug_gui=False)
    client = env.getPyBulletClient()
    print(f"[terrain] raycast-vs-DEM max error {verify_terrain(t, client):.2f} m")
    # 거친 DEM에서는 픽셀 고도와 실제 표면이 다르므로 생성 고도를 실제 표면 기준으로 다시 잡는다
    z_surf = t.surface_z(start[0], start[1], client)
    env.INIT_XYZS[0, 2] = z_surf + 0.1
    pts[0, 2] = z_surf + 0.1
    print(f"[spawn] pixel ground {start[2]-0.1:.1f} m, true surface {z_surf:.1f} m")
    follower = PathFollower(pts, cum, climb_end, env.CTRL_TIMESTEP, speed=args.speed, climb_speed=args.climb_speed,
                            accel=args.accel, max_lag=args.max_lag, max_err=args.max_err, max_err_z=args.max_err_z,
                            vel_tau=args.vel_tau, max_vel_err=args.max_vel_err, max_vel_err_z=args.max_vel_err_z)

    log = {k: [] for k in ["t", "x", "y", "z", "ground", "clearance", "tx", "ty", "tz", "speed"]}
    n_frames = 0
    fdir = os.path.join(args.out, f"{args.island}_frames")
    if args.video:
        os.makedirs(fdir, exist_ok=True)
        for f in os.listdir(fdir): os.remove(os.path.join(fdir, f))
    obs, _ = env.reset()
    action = np.zeros((1, 4)); dt = env.CTRL_TIMESTEP; trace = []
    frame_every = max(1, int(round(args.ctrl_hz / args.video_fps)))
    total_steps = int((cum[-1] / args.speed + args.speed / args.accel + 20) * args.ctrl_hz)
    wall = time.time()
    for i in range(total_steps):
        obs, *_ = env.step(action)
        st = obs[0]; pos, vel = st[0:3], st[10:13]
        action[0] = follower.step(st)
        s, v, desired, target = follower.s, follower.v, follower.desired, follower.target
        if i % 4 == 0:
            g = t.surface_z(pos[0], pos[1], client)
            for k, val in zip(log, [i * dt, pos[0], pos[1], pos[2], g, pos[2] - g, desired[0], desired[1], desired[2], np.linalg.norm(vel)]):
                log[k].append(float(val))
        if args.video and i % frame_every == 0:
            Image.fromarray(chase_frame(client, pos, vel, args.video_w, args.video_w * 5 // 8)).save(os.path.join(fdir, f"{n_frames:05d}.png"))
            n_frames += 1
        if args.gui:
            if i % 6 == 0:
                yaw = np.degrees(np.arctan2(vel[1], vel[0])) - 90 if np.linalg.norm(vel[:2]) > 0.5 else 0.0
                p.resetDebugVisualizerCamera(cameraDistance=12, cameraYaw=yaw, cameraPitch=-20,
                                             cameraTargetPosition=pos.tolist(), physicsClientId=client)
            sync(i, wall, dt / args.speedup)       # 실시간(배속) 페이싱
        if i % (args.ctrl_hz * 30) == 0:
            print(f"[t={i*dt:5.0f}s] pos=({pos[0]:.0f},{pos[1]:.0f},{pos[2]:.0f}) ground={g:.0f} path {100*s/cum[-1]:.0f}% frames={n_frames} wall={time.time()-wall:.0f}s", flush=True)
        trace.append((i * dt, pos.copy(), st[7:10].copy(), desired.copy(), target.copy(), v, float(np.linalg.norm(vel))))
        if len(trace) > 3 * args.ctrl_hz: trace.pop(0)
        if abs(st[7]) > 2.0 or abs(st[8]) > 2.0 or pos[2] < -1.0:
            print(f"[abort] drone flipped or fell through terrain at t={i*dt:.1f} s, pos={np.round(pos,1)}")
            for tt, pp, rr, dd, tg, vv, sp in trace[::12]:
                print(f"   t={tt:6.2f} pos={np.round(pp,1)} rpy={np.round(rr,2)} desired={np.round(dd,1)} target={np.round(tg,1)} v={vv:.1f} |vel|={sp:.1f}")
            break
        if s >= cum[-1] and np.linalg.norm(pts[-1] - pos) < 2.0:
            print(f"[done] reached end of path at t={i*dt:.1f} s"); break
    env.close()
    for k in log: log[k] = np.array(log[k])
    print(f"[sim] {i+1} ctrl steps, {(i+1)*dt:.0f} s sim time in {time.time()-wall:.0f} s wall; "
          f"min clearance {log['clearance'][log['t']>5].min():.1f} m, mean speed {log['speed'][log['t']>5].mean():.1f} m/s, "
          f"max lag behind path point {np.sqrt((log['x']-log['tx'])**2+(log['y']-log['ty'])**2+(log['z']-log['tz'])**2).max():.1f} m")

    np.savetxt(os.path.join(args.out, f"{args.island}_path.csv"), np.column_stack([log[k] for k in log]), delimiter=",",
               header=",".join(log), comments="")
    save_map(t, log, pts, os.path.join(args.out, f"{args.island}_map.png"))
    if n_frames:
        mp4 = os.path.join(args.out, f"{args.island}_flight.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(fdir, "%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4], check=True)
        print(f"[video] {n_frames} frames -> {mp4}")


if __name__ == "__main__":
    main()
