import os
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.autograd import grad
from tensorboardX import SummaryWriter

from cifar10 import CIFAR10
from vgg import vgg11
from utils import *

parser = argparse.ArgumentParser()
parser.add_argument('--maxiter', type=int, default=int(1e5+1))
parser.add_argument('--lr', type=float, default=0.05)
parser.add_argument('--batch-size', type=int, default=100)
parser.add_argument('--resume', type=str, default=None)
parser.add_argument('--datadir', type=str, default='/home/wjf/datasets/CIFAR10/numpy')
parser.add_argument('--logdir', type=str, default='logs/SGD')

args = parser.parse_args()
logger = LogSaver(args.logdir,'logs_sgd')
logger.save(str(args), 'args')

# data
dataset = CIFAR10(args.datadir)
logger.save(str(dataset), 'dataset')
test_list = dataset.getTestList(500, True)

# model
start_iter = 0
model = vgg11().cuda()
logger.save(str(model), 'classifier')
criterion = nn.CrossEntropyLoss().cuda()
optimizer = torch.optim.SGD(model.parameters(), lr=args.lr)
logger.save(str(optimizer), 'optimizer')

if args.resume:
    checkpoint = torch.load(args.resume)
    start_iter = checkpoint['iter']
    model.load_state_dict(checkpoint['model'])
    optimizer.load_state_dict(checkpoint['optimizer'])
    print("=> loaded checkpoint '{}'".format(args.resume))

# writer
writer = SummaryWriter(args.logdir)

# optimization
torch.backends.cudnn.benchmark = True
for i in range(start_iter, args.maxiter):
    # train
    model.train()
    x, y = dataset.getTrainBatch(args.batch_size, True)
    out = model(x)
    loss = criterion(out, y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    # evaluate
    if i % 100 == 0 or i <= 100:
        model.eval()
        out = model(x)
        acc_train = accuracy(out, y).item()
        loss_train = criterion(out, y).item()
        writer.add_scalar('acc/train', acc_train, i)
        writer.add_scalar('loss/train', loss_train, i)

        acc, loss = 0.0, 0.0
        for x,y in test_list:
            out = model(x)
            acc += accuracy(out, y).item()
            loss += criterion(out, y).item()
        acc /= len(test_list)
        loss /= len(test_list)

        writer.add_scalar('acc/test', acc, i)
        writer.add_scalar('loss/test', loss, i)
        writer.add_scalar('acc/diff', acc_train-acc, i)

        logger.save('Iter:%d, Test [acc: %.2f, loss: %.4f], Train [acc: %.2f, loss: %.4f]' \
                % (i, acc, loss, acc_train, loss_train))

    if i % 1000 == 0:
        state = {'iter':i, 'model':model.state_dict(), 'optimizer':optimizer.state_dict()}
        torch.save(state, args.logdir+'/iter-'+str(i)+'.pth.tar')

writer.close()
