# Graph Neural Networks with Pytorch
# Target: Graph Isomorphism Networks
# Original Paper: https://arxiv.org/abs/1810.00826
# Original Code: https://github.com/rusty1s/pytorch_geometric/blob/master/examples/mutag_gin.py

import os
import sys

import torch
import torch.nn.functional as F
from torch.nn import Sequential, Linear, BatchNorm1d, ReLU
from torch_geometric.datasets import TUDataset
from torch_geometric.data import DataLoader
from torch_geometric.nn import GINConv, global_add_pool

sys.path.append('../')
from utils import *
logger = make_logger(name='gin_logger')


# Load TU Dataset
dataset = 'TU'
path = os.path.join(os.getcwd(), 'data', dataset)
dataset = TUDataset(path, name='MUTAG').shuffle()

# dataset length: 188
logger.info(f"Dataset Length: {len(dataset)}")

train_dataset = dataset[len(dataset) // 10:]
test_dataset = dataset[:len(dataset) // 10]

len_train, len_test = len(train_dataset), len(test_dataset)
logger.info("Train:Test: {:.4f}:{:.4f}".format(
    len_train/(len_train+len_test), len_test/(len_train+len_test)))

train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=128)


# Define Model
class GIN(torch.nn.Module):
    def __init__(self, in_channels, dim, out_channels):
        super(GIN, self).__init__()

        self.conv1 = GINConv(
            Sequential(
                Linear(in_channels, dim),
                BatchNorm1d(dim),
                ReLU(),
                Linear(dim, dim),
                ReLU())
        )

        self.conv2 = GINConv(
            Sequential(Linear(dim, dim), BatchNorm1d(dim), ReLU(),
                       Linear(dim, dim), ReLU()))

        self.conv3 = GINConv(
            Sequential(Linear(dim, dim), BatchNorm1d(dim), ReLU(),
                       Linear(dim, dim), ReLU()))

        self.conv4 = GINConv(
            Sequential(Linear(dim, dim), BatchNorm1d(dim), ReLU(),
                       Linear(dim, dim), ReLU()))

        self.conv5 = GINConv(
            Sequential(Linear(dim, dim), BatchNorm1d(dim), ReLU(),
                       Linear(dim, dim), ReLU()))

        self.lin1 = Linear(dim, dim)
        self.lin2 = Linear(dim, out_channels)

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index)
        x = self.conv2(x, edge_index)
        x = self.conv3(x, edge_index)
        x = self.conv4(x, edge_index)
        x = self.conv5(x, edge_index)
        x = global_add_pool(x, batch)
        x = self.lin1(x).relu()
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.lin2(x)
        return F.log_softmax(x, dim=-1)


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = GIN(dataset.num_features, 32, dataset.num_classes).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)


def train():
    model.train()

    total_loss = 0
    for data in train_loader:
        data = data.to(device)
        optimizer.zero_grad()
        output = model(data.x, data.edge_index, data.batch)
        loss = F.nll_loss(output, data.y)
        loss.backward()
        optimizer.step()
        total_loss += float(loss) * data.num_graphs
    return total_loss / len(train_loader.dataset)


@torch.no_grad()
def test(loader):
    model.eval()

    total_correct = 0
    for data in loader:
        data = data.to(device)
        out = model(data.x, data.edge_index, data.batch)
        total_correct += int((out.argmax(-1) == data.y).sum())
    return total_correct / len(loader.dataset)


for epoch in range(1, 101):
    loss = train()
    train_acc = test(train_loader)
    test_acc = test(test_loader)
    print(f'Epoch: {epoch:03d}, Loss: {loss:.4f}, Train Acc: {train_acc:.4f} '
          f'Test Acc: {test_acc:.4f}')

