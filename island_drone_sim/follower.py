"""경로 생성과 Crazyflie PID용 경로추종(캐럿) 로직. fly_island.py와 island_video.py가 공유한다."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl
from gym_pybullet_drones.utils.enums import DroneModel


def build_path(t, center_xy, radius, agl, step=5.0, smooth_px=3.0, start_angle=-np.pi / 2, turns=1.0):
    """center 주위를 반시계로 선회하는 지형추종 경로. 시작점 지면에서 수직 이륙 후 원으로 진입.
    반환: pts (N,3), cum 누적거리, climb_end 상승구간 끝 거리."""
    cx, cy = center_xy
    smooth = gaussian_filter(t.heights, smooth_px)

    def ground_smooth(x, y):
        ix, iy = t.pixel(x, y)
        return float(smooth[iy, ix])

    n = int(2 * np.pi * radius * turns / step)
    ang = start_angle + np.linspace(0, 2 * np.pi * turns, n, endpoint=True)
    circ = np.stack([cx + radius * np.cos(ang), cy + radius * np.sin(ang)], axis=1)
    z = np.array([max(ground_smooth(x, y), 0.0) + agl for x, y in circ])
    z = np.convolve(np.pad(z, 10, mode="edge"), np.ones(21) / 21, mode="valid")
    start = circ[0]
    z0 = t.height_at(*start)
    climb = np.linspace(z0 + 0.1, z[0], int((z[0] - z0) / step) + 2)
    pts = np.vstack([np.column_stack([np.full_like(climb, start[0]), np.full_like(climb, start[1]), climb]),
                     np.column_stack([circ, z])])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    return pts, cum, cum[len(climb) - 1]


def carrot(pts, cum, s):
    s = min(max(s, 0.0), cum[-1])
    i = int(np.searchsorted(cum, s, side="right") - 1)
    i = min(i, len(pts) - 2)
    r = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    return pts[i] + r * (pts[i + 1] - pts[i])


class PathFollower:
    """진행거리 s를 속도 v로 전진시키고, DSLPIDControl에 넘길 목표를 축별로 잘라 안정화한다.

    DSLPIDControl 게인(P=0.4/0.4/1.25 N/m, D=0.2/0.2/0.5)은 27 g Crazyflie 무게 0.265 N 기준이라
    오차를 그대로 넘기면 추력 벡터가 뒤집힌다. 수직은 특히 민감: 0.265 - 1.25*ez - 0.5*evz > 0 유지.
    """

    def __init__(self, pts, cum, climb_end, dt, speed=10.0, climb_speed=3.0, accel=1.0, max_lag=8.0,
                 max_err=0.6, max_err_z=0.08, vel_tau=1.0, max_vel_err=1.5, max_vel_err_z=0.25):
        self.pts, self.cum, self.climb_end, self.dt = pts, cum, climb_end, dt
        self.speed, self.climb_speed, self.accel, self.max_lag = speed, climb_speed, accel, max_lag
        self.max_err, self.max_err_z, self.vel_tau = max_err, max_err_z, vel_tau
        self.max_vel_err, self.max_vel_err_z = max_vel_err, max_vel_err_z
        self.ctrl = DSLPIDControl(drone_model=DroneModel.CF2X)
        self.s = 0.0
        self.v = 0.0
        self.tvel_f = np.zeros(3)
        self.desired = pts[0].copy()
        self.target = pts[0].copy()

    @property
    def done(self):
        return self.s >= self.cum[-1]

    def step(self, state):
        """state: 20차원 드론 상태. 반환: 4개 모터 RPM."""
        pos, vel = state[0:3], state[10:13]
        pts, cum, dt = self.pts, self.cum, self.dt
        v_cap = self.climb_speed if self.s < self.climb_end else self.speed
        self.v = min(self.v + self.accel * dt, v_cap)
        if np.linalg.norm(carrot(pts, cum, self.s) - pos) < self.max_lag:
            self.s = min(self.s + self.v * dt, cum[-1])
        desired = carrot(pts, cum, self.s)
        e = desired - pos
        nxy = np.linalg.norm(e[:2])
        exy = e[:2] / nxy * min(nxy, self.max_err) if nxy > 1e-6 else e[:2]
        ez = np.clip(e[2], -self.max_err_z, self.max_err_z)
        target = pos + np.array([exy[0], exy[1], ez])
        tvel = carrot(pts, cum, min(self.s + 1.0, cum[-1])) - desired
        tvel = tvel / (np.linalg.norm(tvel) + 1e-9) * self.v
        self.tvel_f += (tvel - self.tvel_f) * min(1.0, dt / self.vel_tau)
        dv = self.tvel_f - vel
        nvxy = np.linalg.norm(dv[:2])
        dvxy = dv[:2] / nvxy * min(nvxy, self.max_vel_err) if nvxy > 1e-6 else dv[:2]
        dvz = np.clip(dv[2], -self.max_vel_err_z, self.max_vel_err_z)
        tvel_cmd = vel + np.array([dvxy[0], dvxy[1], dvz])
        self.desired, self.target = desired, target
        rpm, _, _ = self.ctrl.computeControlFromState(control_timestep=dt, state=state, target_pos=target,
                                                      target_vel=tvel_cmd, target_rpy=np.zeros(3))
        return rpm
