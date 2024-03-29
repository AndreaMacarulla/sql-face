# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/08_qmagface.ipynb.

# %% auto 0
__all__ = ['compute_qmagface_embeddings']

# %% ../nbs/08_qmagface.ipynb 4
import os
import tqdm
import numpy as np
import cv2
import torch
import torchvision.transforms
from torch.utils import data
from collections import namedtuple, OrderedDict
from tqdm import tqdm

import torch.nn.functional as F
import torch.nn as nn
import torch

import sys
sys.path.append("..")

# %% ../nbs/08_qmagface.ipynb 6
def conv3x3(in_planes, out_planes, stride=1, groups=1, dilation=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=dilation, groups=groups, bias=False, dilation=dilation)


def conv1x1(in_planes, out_planes, stride=1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)

# %% ../nbs/08_qmagface.ipynb 7
class IBasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1):
        super(IBasicBlock, self).__init__()
        if groups != 1 or base_width != 64:
            raise ValueError(
                'BasicBlock only supports groups=1 and base_width=64')
        if dilation > 1:
            raise NotImplementedError(
                "Dilation > 1 not supported in BasicBlock")
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.bn1 = nn.BatchNorm2d(inplanes, eps=2e-05, momentum=0.9)
        self.conv1 = conv3x3(inplanes, planes)
        self.bn2 = nn.BatchNorm2d(planes, eps=2e-05, momentum=0.9)
        self.prelu = nn.PReLU(planes)
        self.conv2 = conv3x3(planes, planes, stride)
        self.bn3 = nn.BatchNorm2d(planes, eps=2e-05, momentum=0.9)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.bn1(x)
        out = self.conv1(out)
        out = self.bn2(out)
        out = self.prelu(out)
        out = self.conv2(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity

        return out

# %% ../nbs/08_qmagface.ipynb 8
class IResNet(nn.Module):
    fc_scale = 7 * 7

    def __init__(self, block, layers, num_classes=512, zero_init_residual=False,
                 groups=1, width_per_group=64, replace_stride_with_dilation=None):
        super(IResNet, self).__init__()

        self.inplanes = 64
        self.dilation = 1
        if replace_stride_with_dilation is None:
            # each element in the tuple indicates if we should replace
            # the 2x2 stride with a dilated convolution instead
            replace_stride_with_dilation = [False, False, False]
        if len(replace_stride_with_dilation) != 3:
            raise ValueError("replace_stride_with_dilation should be None "
                             "or a 3-element tuple, got {}".format(replace_stride_with_dilation))
        self.groups = groups
        self.base_width = width_per_group
        self.conv1 = nn.Conv2d(3, self.inplanes, kernel_size=3, stride=1, padding=1,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(self.inplanes, eps=2e-05, momentum=0.9)
        self.prelu = nn.PReLU(self.inplanes)
        self.layer1 = self._make_layer(block, 64, layers[0], stride=2)
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2,
                                       dilate=replace_stride_with_dilation[0])
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2,
                                       dilate=replace_stride_with_dilation[1])
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2,
                                       dilate=replace_stride_with_dilation[2])
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))

        self.bn2 = nn.BatchNorm2d(
            512 * block.expansion, eps=2e-05, momentum=0.9)
        self.dropout = nn.Dropout2d(p=0.4, inplace=True)
        self.fc = nn.Linear(512 * block.expansion * self.fc_scale, num_classes)
        self.features = nn.BatchNorm1d(num_classes, eps=2e-05, momentum=0.9)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(
                    m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm2d, nn.GroupNorm)):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, IBasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)

    def _make_layer(self, block, planes, blocks, stride=1, dilate=False):
        downsample = None
        previous_dilation = self.dilation
        if dilate:
            self.dilation *= stride
            stride = 1
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion,
                               eps=2e-05, momentum=0.9),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample, self.groups,
                            self.base_width, previous_dilation))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes, groups=self.groups,
                                base_width=self.base_width, dilation=self.dilation))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.prelu(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.bn2(x)
        x = self.dropout(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        x = self.features(x)

        return x

# %% ../nbs/08_qmagface.ipynb 9
def _iresnet(arch, block, layers, pretrained, progress, **kwargs):
    model = IResNet(block, layers, **kwargs)
    # if pretrained:
    # state_dict = load_state_dict_from_url(model_urls[arch],
    #                                        progress=progress)
    # model.load_state_dict(state_dict)
    return model

def iresnet18(pretrained=False, progress=True, **kwargs):
    return _iresnet('iresnet18', IBasicBlock, [2, 2, 2, 2], pretrained, progress,
                    **kwargs)


def iresnet34(pretrained=False, progress=True, **kwargs):
    return _iresnet('iresnet34', IBasicBlock, [3, 4, 6, 3], pretrained, progress,
                    **kwargs)


def iresnet50(pretrained=False, progress=True, **kwargs):
    return _iresnet('iresnet50', IBasicBlock, [3, 4, 14, 3], pretrained, progress,
                    **kwargs)


def iresnet100(pretrained=False, progress=True, **kwargs):
    return _iresnet('iresnet100', IBasicBlock, [3, 13, 30, 3], pretrained, progress,
                    **kwargs)

# %% ../nbs/08_qmagface.ipynb 11
def load_features(args):
    if args.arch == 'iresnet34':
        features = iresnet34(
            pretrained=False,
            num_classes=args.embedding_size,
        )
    elif args.arch == 'iresnet18':
        features = iresnet18(
            pretrained=False,
            num_classes=args.embedding_size,
        )
    elif args.arch == 'iresnet50':
        features = iresnet50(
            pretrained=False,
            num_classes=args.embedding_size,
        )
    elif args.arch == 'iresnet100':
        features = iresnet100(
            pretrained=False,
            num_classes=args.embedding_size,
        )
    else:
        raise ValueError()
    return features

# %% ../nbs/08_qmagface.ipynb 12
def load_dict_inf(args, model):
    if os.path.isfile(args.resume):
        print('=> loading pth from {} ...'.format(args.resume))
        if args.cpu_mode:
            checkpoint = torch.load(args.resume, map_location=torch.device("cpu"))
        else:
            checkpoint = torch.load(args.resume)
        _state_dict = clean_dict_inf(model, checkpoint['state_dict'])
        model_dict = model.state_dict()
        model_dict.update(_state_dict)
        model.load_state_dict(model_dict)
        # delete to release more space
        del checkpoint
        del _state_dict
    else:
        sys.exit("=> No checkpoint found at '{}'".format(args.resume))
    return model

# %% ../nbs/08_qmagface.ipynb 13
def clean_dict_inf(model, state_dict):
    _state_dict = OrderedDict()
    for k, v in state_dict.items():
        # # assert k[0:1] == 'features.module.'
        new_k = 'features.'+'.'.join(k.split('.')[2:])
        if new_k in model.state_dict().keys() and \
           v.size() == model.state_dict()[new_k].size():
            _state_dict[new_k] = v
        # assert k[0:1] == 'module.features.'
        new_kk = '.'.join(k.split('.')[1:])
        if new_kk in model.state_dict().keys() and \
           v.size() == model.state_dict()[new_kk].size():
            _state_dict[new_kk] = v
    num_model = len(model.state_dict().keys())
    num_ckpt = len(_state_dict.keys())
    if num_model != num_ckpt:
        sys.exit("=> Not all weights loaded, model params: {}, loaded params: {}".format(
            num_model, num_ckpt))
    return _state_dict

# %% ../nbs/08_qmagface.ipynb 14
class NetworkBuilder_inf(nn.Module):
    def __init__(self, args):
        super(NetworkBuilder_inf, self).__init__()
        self.features = load_features(args)

    def forward(self, input):
        # add Fp, a pose feature
        x = self.features(input)
        return x

# %% ../nbs/08_qmagface.ipynb 15
def builder_inf(args):
    model = NetworkBuilder_inf(args)
    # Used to run inference
    model = load_dict_inf(args, model)
    return model

# %% ../nbs/08_qmagface.ipynb 16
# model_path = os.path.join('models', 'qmagface', 'magface_epoch_00025.pth')


def load_model(model_path = os.path.join('models', 'qmagface', 'magface_epoch_00025.pth')):
    Args = namedtuple('Args', ['arch', 'resume', 'embedding_size', 'cpu_mode'])
    args = Args('iresnet100', model_path, 512, True)
    model = builder_inf(args)
    model = torch.nn.DataParallel(model)
    model.eval()
    return model

# %% ../nbs/08_qmagface.ipynb 17
def compute_qmagface_embeddings(aligned_img:np.array, model)->np.array:    
    trans = torchvision.transforms.ToTensor()
    input_ = trans(aligned_img)
    input_ = input_.unsqueeze(0)
    with torch.no_grad():
        embedding = model(input_).to('cpu')
    return embedding.squeeze().numpy() 
