"""실제 섬 DEM 위를 도는 드론을 3인칭 상공 시점으로 촬영한 영상 생성.

구성: (1) 섬 전경 선회 샷 -> (2) 드론 뒤·위에서 따라가는 3인칭 추적 샷 -> (3) 수직 상승 풀백 샷.
물리는 gym-pybullet-drones의 Crazyflie + PID이고, 화면의 드론은 멀리서도 보이도록 키운 시각용
프록시 모델(기본 팔 길이 15 m)이다. 하늘과 원거리 안개는 깊이·세그먼트 버퍼로 후합성한다.

예:  python island_video.py --island gyodong --out results
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

from follower import PathFollower, build_path
from island_aviary import IslandAviary
from terrain import ISLANDS, hypsometric_texture, load_dem

SKY_TOP = np.array([72, 132, 205], float)
SKY_HORIZON = np.array([205, 222, 238], float)


def make_drone_proxy(client, arm=15.0):
    """시각용 쿼드콥터: X자 팔 2개 + 로터 4개 + 몸체. 질량 0, 충돌 없음."""
    r = arm * 0.28
    shapes = [
        dict(shapeType=p.GEOM_BOX, halfExtents=[arm, arm * 0.06, arm * 0.04], rgbaColor=[0.12, 0.12, 0.14, 1],
             visualFramePosition=[0, 0, 0], visualFrameOrientation=p.getQuaternionFromEuler([0, 0, np.pi / 4])),
        dict(shapeType=p.GEOM_BOX, halfExtents=[arm, arm * 0.06, arm * 0.04], rgbaColor=[0.12, 0.12, 0.14, 1],
             visualFramePosition=[0, 0, 0], visualFrameOrientation=p.getQuaternionFromEuler([0, 0, -np.pi / 4])),
        dict(shapeType=p.GEOM_BOX, halfExtents=[arm * 0.3, arm * 0.3, arm * 0.12], rgbaColor=[0.9, 0.25, 0.1, 1],
             visualFramePosition=[0, 0, arm * 0.08], visualFrameOrientation=[0, 0, 0, 1]),
    ]
    for k in range(4):
        a = np.pi / 4 + k * np.pi / 2
        shapes.append(dict(shapeType=p.GEOM_CYLINDER, radius=r, length=arm * 0.03, rgbaColor=[0.85, 0.85, 0.9, 1],
                           visualFramePosition=[arm * np.cos(a), arm * np.sin(a), arm * 0.08],
                           visualFrameOrientation=[0, 0, 0, 1]))
    vis = p.createVisualShapeArray(
        shapeTypes=[s["shapeType"] for s in shapes],
        halfExtents=[s.get("halfExtents", [0, 0, 0]) for s in shapes],
        radii=[s.get("radius", 0) for s in shapes],
        lengths=[s.get("length", 0) for s in shapes],
        rgbaColors=[s["rgbaColor"] for s in shapes],
        visualFramePositions=[s["visualFramePosition"] for s in shapes],
        visualFrameOrientations=[s["visualFrameOrientation"] for s in shapes],
        physicsClientId=client)
    return p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[0, 0, -1000], physicsClientId=client)


def add_sea_plane(client, size=400000.0, top_z=-2.0):
    """지형 밖까지 이어지는 바다 평면(시각 전용). 윗면이 top_z (heightfield의 바다 0 m보다 살짝 아래)."""
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[size / 2, size / 2, 1.0], rgbaColor=[0.10, 0.28, 0.55, 1],
                              physicsClientId=client)
    return p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[0, 0, top_z - 1.0], physicsClientId=client)


def render(client, eye, target, w, h, fov, near=5.0, far=80000.0, shadow=0):
    view = p.computeViewMatrix(list(eye), list(target), [0, 0, 1], physicsClientId=client)
    proj = p.computeProjectionMatrixFOV(fov, w / h, near, far, physicsClientId=client)
    _, _, rgb, depth, seg = p.getCameraImage(w, h, view, proj, renderer=p.ER_TINY_RENDERER, shadow=shadow,
                                             lightDirection=[0.4, 0.25, 1.0], lightAmbientCoeff=0.55,
                                             lightDiffuseCoeff=0.55, lightSpecularCoeff=0.0, physicsClientId=client)
    rgb = np.reshape(rgb, (h, w, 4))[..., :3].astype(float)
    depth = np.reshape(depth, (h, w)).astype(float)
    seg = np.reshape(seg, (h, w))
    # 하늘: 아무것도 없는 픽셀 -> 위에서 '지평선 행'까지 그라데이션 (열마다 마지막 하늘 행 기준)
    sky_mask = seg < 0
    rows = np.arange(h)[:, None]
    # 바다 지평선은 수평선이므로 열별 값 중 가장 아래(최대)를 전역 지평선 행으로 쓴다 (산 봉우리 주변 후광 방지)
    last_sky = np.where(sky_mask.any(axis=0), h - 1 - np.argmax(sky_mask[::-1], axis=0), 0)
    horizon = max(int(last_sky.max()), 1)
    vv = np.clip(rows / horizon, 0, 1)[..., None] ** 0.8
    sky = SKY_TOP * (1 - vv) + SKY_HORIZON * vv
    out = np.where(sky_mask[..., None], sky, rgb)
    # 원거리 안개: 선형 깊이 기준으로 지평선 색과 혼합 (3 km부터 시작, 30 km에서 최대 75%)
    lin = far * near / (far - (far - near) * depth)
    fog = (np.clip((lin - 3000.0) / 27000.0, 0, 1) ** 0.7 * 0.75)[..., None]
    out = np.where(sky_mask[..., None], out, out * (1 - fog) + SKY_HORIZON * fog)
    return out.clip(0, 255).astype(np.uint8)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--island", default="gyodong", choices=list(ISLANDS))
    ap.add_argument("--radius", type=float, default=None, help="선회 반경(m); 기본 = 섬 긴 변의 0.42배(해안 근처)")
    ap.add_argument("--agl", type=float, default=120.0, help="지형 위 비행고도(m)")
    ap.add_argument("--speed", type=float, default=10.0)
    ap.add_argument("--sim_per_frame", type=float, default=2.5, help="영상 1프레임당 시뮬 시간(s) = 타임랩스 배율/fps")
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--max_frames", type=int, default=1200)
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--height", type=int, default=540)
    ap.add_argument("--fov", type=float, default=60.0)
    ap.add_argument("--proxy_arm", type=float, default=20.0, help="화면용 드론 모델 팔 길이(m)")
    ap.add_argument("--cam_back", type=float, default=180.0, help="3인칭 카메라: 드론 뒤 거리(m)")
    ap.add_argument("--cam_up", type=float, default=120.0, help="3인칭 카메라: 드론 위 높이(m)")
    ap.add_argument("--intro_frames", type=int, default=90, help="섬 전경 샷 프레임 수")
    ap.add_argument("--outro_frames", type=int, default=60, help="마지막 수직 풀백 프레임 수")
    ap.add_argument("--shadow", action="store_true")
    ap.add_argument("--z_scale", type=float, default=1.5, help="지형 수직 과장 배율(평탄한 섬의 입체감용; 물리·경로에도 동일 적용)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--tiles", default="tiles")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    t = load_dem(args.island, args.tiles)
    t.heights = t.heights * args.z_scale
    tex = hypsometric_texture(t, os.path.join(args.out, f"{args.island}_tex.png"))
    cx, cy = t.center_xy if t.center_xy is not None else t.land_centroid()
    ext = max(t.land_extent_m(), 2.2 * (t.orbit_radius or 0))
    radius = args.radius or t.orbit_radius or 0.42 * ext
    ex, ey = t.extent_m()
    print(f"[terrain] {args.island}: {t.cols}x{t.rows} px, {t.mpp:.1f} m/px, {ex/1000:.1f} x {ey/1000:.1f} km; "
          f"island centroid ({cx:.0f},{cy:.0f}), extent {ext/1000:.1f} km, peak {t.peak()[2]:.0f} m; orbit radius {radius:.0f} m")

    pts, cum, climb_end = build_path(t, (cx, cy), radius, args.agl, start_angle=-np.pi / 2)
    print(f"[path] length {cum[-1]:.0f} m -> {cum[-1]/args.speed:.0f} s flight, "
          f"{min(args.max_frames, int(cum[-1]/args.speed/args.sim_per_frame))} chase frames at {args.sim_per_frame} s/frame")

    env = IslandAviary(terrain=t, texture_path=tex, drone_model=DroneModel.CF2X, num_drones=1,
                       initial_xyzs=pts[0].reshape(1, 3), initial_rpys=np.zeros((1, 3)), physics=Physics.PYB,
                       pyb_freq=240, ctrl_freq=48, gui=False, obstacles=False, user_debug_gui=False)
    client = env.getPyBulletClient()
    env.INIT_XYZS[0, 2] = t.surface_z(pts[0][0], pts[0][1], client) + 0.1
    pts[0, 2] = env.INIT_XYZS[0, 2]
    obs, _ = env.reset()
    add_sea_plane(client)
    proxy = make_drone_proxy(client, args.proxy_arm)
    follower = PathFollower(pts, cum, climb_end, env.CTRL_TIMESTEP, speed=args.speed)

    fdir = os.path.join(args.out, f"{args.island}_video_frames")
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        os.remove(os.path.join(fdir, f))

    W, H = args.width, args.height
    steps_per_frame = max(1, int(round(args.sim_per_frame * env.CTRL_FREQ)))
    action = np.zeros((1, 4))
    heading = np.array([1.0, 0.0, 0.0])
    eye_prev = None
    n = 0
    wall = time.time()

    def set_proxy(st):
        p.resetBasePositionAndOrientation(proxy, st[0:3].tolist(), st[3:7].tolist(), physicsClientId=client)

    def follow_cam(st, hd):
        pos = st[0:3]
        eye = pos - hd * args.cam_back + np.array([0, 0, args.cam_up])
        eye[2] = max(eye[2], t.surface_z(eye[0], eye[1], client) + 15.0)
        tgt = pos + hd * 60.0
        return eye, tgt

    def save(img):
        nonlocal n
        Image.fromarray(img).save(os.path.join(fdir, f"{n:05d}.png"))
        n += 1

    # ---- (1) 섬 전경: 멀리서 섬 중심을 보며 60도 선회. 드론은 이륙 대기.
    st = obs[0]
    set_proxy(st)
    far_d, far_h = 1.15 * ext, 0.55 * ext
    for k in range(args.intro_frames):
        a = np.radians(-100 + 60 * k / max(args.intro_frames - 1, 1))
        eye = np.array([cx + far_d * np.cos(a), cy + far_d * np.sin(a), far_h])
        save(render(client, eye, np.array([cx, cy, 0.0]), W, H, args.fov, shadow=int(args.shadow)))
        if k % 30 == 0:
            print(f"[intro] frame {n} wall={time.time()-wall:.0f}s", flush=True)
    intro_eye, intro_tgt = eye, np.array([cx, cy, 0.0])

    # ---- (2) 3인칭 추적: 이륙 직후 전경 카메라에서 추적 카메라로 부드럽게 전환
    blend_frames = 30
    k = 0
    while n < args.intro_frames + args.max_frames and not (follower.done and np.linalg.norm(pts[-1] - st[0:3]) < 3.0):
        for _ in range(steps_per_frame):
            obs, *_ = env.step(action)
            st = obs[0]
            action[0] = follower.step(st)
        set_proxy(st)
        vel = st[10:13]
        if np.linalg.norm(vel[:2]) > 0.5:
            hd_new = np.array([vel[0], vel[1], 0.0]) / np.linalg.norm(vel[:2])
            heading = heading * 0.7 + hd_new * 0.3
            heading /= np.linalg.norm(heading)
        eye, tgt = follow_cam(st, heading)
        if k < blend_frames:
            w = smoothstep(k / blend_frames)
            eye = intro_eye * (1 - w) + eye * w
            tgt = intro_tgt * (1 - w) + tgt * w
        if eye_prev is not None:                      # 카메라 떨림 완화
            eye = eye_prev * 0.5 + eye * 0.5
        eye_prev = eye
        save(render(client, eye, tgt, W, H, args.fov, shadow=int(args.shadow)))
        if k % 30 == 0:
            pos = st[0:3]
            print(f"[chase] frame {n} sim t={follower.s/max(follower.v,0.1):.0f}s path {100*follower.s/cum[-1]:.0f}% "
                  f"pos=({pos[0]:.0f},{pos[1]:.0f},{pos[2]:.0f}) wall={time.time()-wall:.0f}s", flush=True)
        k += 1

    # ---- (3) 풀백: 드론 위로 수직 상승하며 섬 전체가 보이도록
    pos = st[0:3]
    for k in range(args.outro_frames):
        w = smoothstep(k / max(args.outro_frames - 1, 1))
        eye0, tgt0 = follow_cam(st, heading)
        eye1 = np.array([cx, cy - 0.2 * ext, 1.6 * ext])
        eye = eye0 * (1 - w) + eye1 * w
        tgt = pos * (1 - w) + np.array([cx, cy, 0.0]) * w
        save(render(client, eye, tgt, W, H, args.fov, shadow=int(args.shadow)))
    env.close()

    mp4 = os.path.join(args.out, f"{args.island}_video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", os.path.join(fdir, "%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", mp4], check=True)
    print(f"[video] {n} frames ({n/args.fps:.0f} s at {args.fps} fps) -> {mp4}; wall {time.time()-wall:.0f}s")


if __name__ == "__main__":
    main()
