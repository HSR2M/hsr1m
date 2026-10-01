"""gym-pybullet-drones의 CtrlAviary를 실제 섬 지형 위에서 돌리는 환경."""
from __future__ import annotations

import pybullet as p

from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary

from terrain import Terrain, add_terrain_to_pybullet


class IslandAviary(CtrlAviary):
    """기본 평면(plane.urdf) 대신 DEM heightfield를 지면으로 쓰는 CtrlAviary.

    reset() 때마다 BaseAviary._housekeeping()이 월드를 다시 만들기 때문에
    여기서 평면을 제거하고 지형을 다시 올린다.
    """

    def __init__(self, terrain: Terrain, texture_path: str | None = None, **kwargs):
        self.terrain = terrain
        self.texture_path = texture_path
        super().__init__(**kwargs)

    def _housekeeping(self):
        super()._housekeeping()
        p.removeBody(self.PLANE_ID, physicsClientId=self.CLIENT)
        self.PLANE_ID = add_terrain_to_pybullet(self.terrain, self.CLIENT, self.texture_path)
