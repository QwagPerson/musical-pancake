import pathlib
import random
import os

import lightning as L
import torch
from lightning import Trainer

from lightning.pytorch.callbacks import EarlyStopping
from argparse import ArgumentParser

import polyscope as ps

from dataset.lightning_voxel_dataset import VoxelDataModule
from dataset.voxel_dataset import VoxelDataset
from torch.utils.data import DataLoader, random_split

from model.prsnet.lightning_prsnet import LightingPRSNet
from model.prsnet.losses import ChamferLoss, batch_apply_symmetry, apply_symmetry
from setup.setup_voxel_dataset.symmetry_plane import SymmetryPlane
from model.prsnet.metrics import get_phc, transform_representation, undo_transform_representation, get_diagonals_length
from model.prsnet.lightning_prsnet import reverse_points_scaling_transformation, reverse_plane_scaling_transformation


def visualize_prediction(pred_planes, points, real_planes):
    """
    :param pred_planes: N x 7
    :param points: S x 3
    :param real_planes: M x 6 Are scaled!
    """
    # Create symmetryPlane Objs
    original_symmetries = [
        SymmetryPlane(
            point=real_planes[idx, 3::].detach().numpy(),
            normal=real_planes[idx, 0:3].detach().numpy()
        )
        for idx in range(real_planes.shape[0])
    ]

    predicted_symmetries = [
        SymmetryPlane(
            point=pred_planes[idx, 3::].detach().numpy(),
            normal=pred_planes[idx, 0:3].detach().numpy()
        )
        for idx in range(pred_planes.shape[0])
    ]

    other_rep_pred_planes = undo_transform_representation(pred_planes.unsqueeze(0)).squeeze(dim=0)
    # Reflect points
    reflected_points = [
        apply_symmetry(points, other_rep_pred_planes[idx, 0:3], other_rep_pred_planes[idx, 3].unsqueeze(dim=0))
        for idx in range(other_rep_pred_planes.shape[0])
    ]
    # Visualize
    ps.init()
    ps.remove_all_structures()

    ps.register_point_cloud("original pcd", points.detach().numpy())

    for idx, sym_plane in enumerate(original_symmetries):
        ps.register_surface_mesh(
            f"original_sym_plane_{idx}",
            sym_plane.coords,
            sym_plane.trianglesBase,
            smooth_shade=True,
            enabled=False,
        )

    for idx, sym_plane in enumerate(predicted_symmetries):
        ps.register_surface_mesh(
            f"predicted_sym_plane_{idx}",
            sym_plane.coords,
            sym_plane.trianglesBase,
            smooth_shade=True,
            enabled=False,
        )


    for idx, ref_points in enumerate(reflected_points):
        ps.register_point_cloud(f"reflected_points_{idx}", ref_points.detach().numpy(), enabled=False, )

    ps.show()


def visualize_prediction_results(prediction, visualize_unscaled=True):
    """
    :param prediction:
    :param visualize_unscaled:
    :return:
    """
    prediction = [x.float() for x in prediction]
    fig_idx, y_out, sample_points_out, y_pred, sample_points, y_true, y_true_out = prediction
    batch_size = sample_points_out.shape[0]

    for batch_idx in range(batch_size):
        if visualize_unscaled:
            visualize_prediction(
                pred_planes=y_out[batch_idx, :, :],
                real_planes=y_true_out[batch_idx, :, :],
                points=sample_points_out[batch_idx, :, :]
            )
        else:
            visualize_prediction(
                pred_planes=y_pred[batch_idx, :, :],
                real_planes=y_true[batch_idx, :, :],
                points=sample_points[batch_idx, :, :]
            )


if __name__ == "__main__":
    MODEL_PATH = "local_logs/lightning_logs/version_1/checkpoints/epoch=8-step=54.ckpt"
    model = LightingPRSNet.load_from_checkpoint(MODEL_PATH)
    data_module = VoxelDataModule(
        test_data_path="/data/voxel_dataset_v2",
        train_val_split=1,
        batch_size=1,
        sample_size=-1,
        shuffle=False
    )
    trainer = Trainer(enable_progress_bar=False)
    trainer.test(model, data_module)
    predictions_results = trainer.predict(model, data_module)
    for pred in predictions_results:
        visualize_prediction_results(pred, visualize_unscaled=False)
        break