import os
import unittest

import torch
from dotenv import load_dotenv

from model.prsnet.sym_loss import SymLoss, apply_symmetry, batch_dot
from dataset.voxel_dataset import VoxelDataset


class TestSymLoss(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sym_loss = SymLoss(reg_coef=0)
        AMBIENTE = "local"
        ENV_PATH = f"envs/.{AMBIENTE}.env"
        env = load_dotenv(ENV_PATH)
        if not env:
            raise ValueError(f"Failed to load env, path used is {ENV_PATH}")
        cls.dataset = VoxelDataset(os.environ.get("VOXEL_DATASET_ROOT"))

    def test_batch_dot_function(self):
        a = torch.rand(10, 3)
        b = torch.rand(3)
        result = batch_dot(a, b)
        expected_result = torch.zeros(10)
        for i in range(expected_result.shape[0]):
            for j in range(b.shape[0]):
                expected_result[i] += a[i, j] * b[j]
        self.assertTrue(
            torch.equal(result, expected_result),
            f"Bug in batch_dot function.\n"
            f"Expected {expected_result}\n"
            f"Got {result}\n"
        )
        pass

    def test_apply_symmetry_function(self):
        # Simple symmetry on y plane
        self.assertTrue(
            torch.equal(
                torch.tensor([
                    [0.0, 1.0, 0.0], [0.0, -1.0, 0.0]
                ]),
                apply_symmetry(
                    points=torch.tensor([
                        [0.0, -1.0, 0.0], [0.0, 1.0, 0.0]
                    ]),
                    normal=torch.tensor([0.0, 1.0, 0.0]),
                    d=torch.tensor(0)
                )
            )
        )

        # Simple symmetry on x plane
        self.assertTrue(
            torch.equal(
                torch.tensor([
                    [1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]
                ]),
                apply_symmetry(
                    points=torch.tensor([
                        [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]
                    ]),
                    normal=torch.tensor([1.0, 0.0, 0.0]),
                    d=torch.tensor(0)
                )
            )
        )

        # Simple symmetry on z plane
        self.assertTrue(
            torch.equal(
                torch.tensor([
                    [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]
                ]),
                apply_symmetry(
                    points=torch.tensor([
                        [0.0, 0.0, -1.0], [0.0, 0.0, 1.0]
                    ]),
                    normal=torch.tensor([0.0, 0.0, 1.0]),
                    d=torch.tensor(0)
                )
            )
        )

        # Simple case where d!=0
        self.assertTrue(
            torch.equal(
                torch.tensor([
                    [0.0, 0.0, 2.0], [0.0, 0.0, 0.0]
                ]),
                apply_symmetry(
                    points=torch.tensor([
                        [0.0, 0.0, 0.0], [0.0, 0.0, 2.0]
                    ]),
                    normal=torch.tensor([0.0, 0.0, 1.0]),
                    d=torch.tensor(-1)
                )
            )
        )

    def test_against_real_figures(self):
        points, voxel, cp, syms = self.dataset[0]
        for idx in range(syms.shape[0]):
            sym = syms[idx, :]
            d = -torch.dot(sym[0:3], sym[3::])
            input_sym = sym[0:4]
            input_sym[3] = d
            symmetry_error = self.sym_loss.planar_reflective_sym_distance_loss(
                input_sym, points, voxel, cp
            )
            self.assertTrue(
                torch.eq(
                    symmetry_error,
                    torch.tensor(0).double()
                ), msg=f"Sym: {input_sym}, Expected 0 got: {symmetry_error}")
