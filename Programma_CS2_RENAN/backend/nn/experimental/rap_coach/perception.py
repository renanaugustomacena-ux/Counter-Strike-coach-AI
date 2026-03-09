import torch
import torch.nn as nn

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.experimental.rap_coach.perception")


class ResNetBlock(nn.Module):
    """
    Canonical Residual Block (Layer 1_4 Formal Foundation).
    Enforces identity shortcut to preserve gradient norm.
    """

    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(
            out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.shortcut = self._create_shortcut(in_channels, out_channels, stride)

    def _create_shortcut(self, in_c, out_c, stride):
        if stride == 1 and in_c == out_c:
            return nn.Sequential()
        return nn.Sequential(
            nn.Conv2d(in_c, out_c, 1, stride=stride, bias=False), nn.BatchNorm2d(out_c)
        )

    def forward(self, x):
        identity = self.shortcut(x)
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += identity
        out = self.relu(out)
        return out


class RAPPerception(nn.Module):
    """
    Multi-Module Perception Layer.
    Implements Ventral (View) and Dorsal (Map) streams.
    """

    def __init__(self):
        super().__init__()
        # [1,2,2,1] = 5 effective ResNet blocks, calibrated for 64x64 training inputs
        # (TrainingTensorConfig). The original [3,4,6,3] (15 blocks) was designed for
        # 224x224 inputs and wasted compute on 64x64 where feature maps collapse after
        # the first stride-2 block. AdaptiveAvgPool2d handles any spatial resolution,
        # so this change is architecture-safe. Any stale checkpoint will be auto-detected
        # by load_nn() which raises StaleCheckpointError. (F3-29)
        self.view_backbone = self._make_resnet_stack(3, 64, [1, 2, 2, 1])
        self.view_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.map_backbone = self._make_resnet_stack(3, 32, [2, 2])
        self.map_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.motion_conv = self._create_motion_conv()
        logger.debug("RAPPerception initialized: view=[1,2,2,1], map=[2,2], motion_conv")

    def _create_motion_conv(self):
        return nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )

    def _make_resnet_stack(self, in_planes, out_planes, num_blocks):
        layers = []
        planes = out_planes
        layers.append(ResNetBlock(in_planes, planes, stride=2))
        for _ in range(sum(num_blocks) - 1):
            layers.append(ResNetBlock(planes, planes, stride=1))
        return nn.Sequential(*layers)

    def forward(self, view_frame, map_frame, motion_diff):
        """
        Extracts spatial and temporal features.
        """
        z_view = self.view_backbone(view_frame)
        z_view = self.view_pool(z_view).flatten(1)

        z_map = self.map_backbone(map_frame)
        z_map = self.map_pool(z_map).flatten(1)

        z_motion = self.motion_conv(motion_diff).flatten(1)

        return torch.cat([z_view, z_map, z_motion], dim=1)
