#!/usr/bin/env python
# coding: utf-8 %%

import numpy as np
import pandas as pd
import pickle
import glob
import copy
import torch as t
import re
import torch
import time
import argparse
from tqdm import tqdm
import torch.nn as nn
import os
import random
from exBERT import BertTokenizer, BertAdam #AdamW 
import tensorflow as tf


ap = argparse.ArgumentParser()
ap.add_argument("-e", "--epochs", required = True, type = int, help='number of training epochs')
ap.add_argument("-b", "--batchsize", required = True, type = int, help='training batchsize')
ap.add_argument("-sp","--save_path",required = True, type = str, help='path to storaget the loss table, stat_dict')
ap.add_argument('-dv','--device',required = True, type = int,nargs='+',help='gpu id for the training, ex [-dv 0 1 2 3]')
ap.add_argument('-lr','--learning_rate',required = True, type = float, help='learning rate , google use 1e-04')
ap.add_argument('-str','--strategy',required = True, type = str, help='choose a strategy from [exBERT], [sciBERT], [bioBERT]')
ap.add_argument('-config','--config',required = True, type = str, nargs = '+', help='dir to the config file')
ap.add_argument('-vocab','--vocab',required = True, type = str, help='path to the vocab file for tokenization')
ap.add_argument('-pm_p','--pretrained_model_path',default = None, type = str, help='path to the pretrained_model stat_dict (torch state_dict)')
ap.add_argument('-pm_p_tf','--pretrained_model_path_tf',default = None, type = str, help='path to the pretrained_model (tensorflow .ckpt)')
ap.add_argument('-dp','--datat_path',required = True, type = str, help='path to data ')
ap.add_argument('-ls','--longest_sentence', required = True, type = int, help='set the limit of the sentence lenght, recommand the same to the -dt')
ap.add_argument('-train_p','--train_p', default=1000, type=int, help='train proportion in load data')
ap.add_argument('-sep','--sep', default = 1, type = int, help = 'sep the training process of aepoch in to N ')
ap.add_argument('-wp', '--warmup', default=-1, type=float, help='portion of all training itters to warmup, -1 means not using warmup')
ap.add_argument('-t_ex_only','--train_extension_only', default=True, type=bool, help='train only the extension module')
ap.add_argument('-val_p','--val_p', default=1000, type=int, help='val proportion in load data')

args = vars(ap.parse_args())
for ii, item in enumerate(args):
    print(item+': '+str(args[item]))
    
## set device
if args['device'] == [-1]:
    device = 'cpu'
    device_ids = 'cpu'
else:
    device_ids = args['device']
    # device = 'cuda:'+str(device_ids[0])
    device = 'mps'
    print('training with GPU: '+str(device_ids))


class pre_train_BertTokenizer(BertTokenizer):
    def __init__(self, vocab_file, **kwargs):
        '''
        
        '''
        super(pre_train_BertTokenizer,self).__init__(vocab_file)
        self.mask_id = self.convert_tokens_to_ids(self.tokenize('[MASK]'))[0]
        self.sep_id = self.convert_tokens_to_ids(self.tokenize('[SEP]'))[0]

    def Masking(self, Input_ids, Masked_lm_labels):
        copyInput_ids = copy.deepcopy(Input_ids)
        rd_1 = np.random.random(Input_ids.shape)
        rd_1[:,0] = 0
        Masked_lm_labels[rd_1>0.85] = Input_ids[rd_1>0.85]
        Input_ids[rd_1>=0.88] = self.mask_id
        Input_ids[(rd_1>=0.865)*(rd_1<0.88)] = (np.random.rand(((rd_1>=0.865)*(rd_1<0.88)*1).sum())*len(self.vocab)).astype(int)
        Input_ids[copyInput_ids==0] = 0
        Masked_lm_labels[copyInput_ids==0] = -1
        return Input_ids, Masked_lm_labels

    def prepare_batch(self, Train_Data,Train_Label, batch_size=args['batchsize'], longest_sentence=128):
        Input_ids = np.zeros((batch_size,longest_sentence))
        Token_type_ids = np.zeros((batch_size,longest_sentence))
        Attention_mask = np.zeros((batch_size,longest_sentence))
        Masked_lm_labels = (np.ones((batch_size,longest_sentence))*-1)
        Next_sentence_label = np.zeros((batch_size))
        
        for ii in range(batch_size): 
            if 0 <= ii < len(Train_Data):
                temp = self.convert_tokens_to_ids(self.tokenize(Train_Data[ii]))
                # print(f"Processing index {ii}") #debug
            else:
                print(f"Index {ii} is out of range.")
            # temp = self.convert_tokens_to_ids(self.tokenize(Train_Data[ii]))
            if len(temp) > longest_sentence:
                sentence_length = longest_sentence
            else:
                sentence_length = len(temp)
            Input_ids[ii,0:sentence_length] = temp[0:sentence_length]
            if self.sep_id in Input_ids[ii]:
                Token_type_ids[ii,np.where(Input_ids[ii]==self.sep_id)[0][0]+1:sentence_length] = 1
            else:
                Token_type_ids[ii,:] = 0
            Attention_mask[ii,0:sentence_length] = 1
        Next_sentence_label = Train_Label
        Input_ids, Masked_lm_labels = self.Masking(Input_ids, Masked_lm_labels)
        return Input_ids,Token_type_ids,Attention_mask,Masked_lm_labels,Next_sentence_label


tok = pre_train_BertTokenizer(args['vocab'])

if args['strategy'] == 'exBERT':
    from exBERT import BertForPreTraining, BertConfig
    bert_config_1 = BertConfig.from_json_file(args['config'][0])
    
    bert_config_2 = BertConfig.from_json_file(args['config'][1])
    
    
    print("Building PyTorch model from configuration: {}".format(str(bert_config_1)))
    print("Building PyTorch model from configuration: {}".format(str(bert_config_2)))
    model = BertForPreTraining(bert_config_1, bert_config_2)
else:
    from exBERT import BertForPreTraining, BertConfig
    bert_config_1 = BertConfig.from_json_file(args['config'][0])
    print("Building PyTorch model from configuration: {}".format(str(bert_config_1)))
    model = BertForPreTraining(bert_config_1)

## load pre-trained model
if args['pretrained_model_path'] is not None:
    stat_dict = t.load(args['pretrained_model_path'], map_location='cpu')
    model.load_state_dict(stat_dict, strict=False)
    
if args['pretrained_model_path_tf'] is not None:
    tf_path = os.path.abspath(args['pretrained_model_path_tf'])
    # Load weights from TF model
    init_vars = tf.train.list_variables(tf_path)
    names = []
    arrays = []
    for name, shape in init_vars:
        print("Loading TF weight {} with shape {}".format(name, shape))
        array = tf.train.load_variable(tf_path, name)
        names.append(name)
        arrays.append(array)

    for name, array in zip(names, arrays):
        name = name.split("/")
        pointer = model
        for m_name in name:
            if re.fullmatch(r"[A-Za-z]+_\d+", m_name):
                scope_names = re.split(r"_(\d+)", m_name)
            else:
                scope_names = [m_name]
            if scope_names[0] == "kernel" or scope_names[0] == "gamma":
                pointer = getattr(pointer, "weight")
            elif scope_names[0] == "output_bias" or scope_names[0] == "beta":
                pointer = getattr(pointer, "bias")
            elif scope_names[0] == "output_weights":
                pointer = getattr(pointer, "weight")
            elif scope_names[0] == "squad":
                pointer = getattr(pointer, "classifier")
            else:
                try:
                    pointer = getattr(pointer, scope_names[0])
                except AttributeError:
                    print("Skipping {}".format("/".join(name)))
                    continue
            if len(scope_names) >= 2:
                num = int(scope_names[1])
                pointer = pointer[num]
        if m_name[-11:] == "_embeddings":
            pointer = getattr(pointer, "weight")
        elif m_name == "kernel":
            array = np.transpose(array)
        try:
            assert (
                pointer.shape == array.shape
            ), f"Pointer shape {pointer.shape} and array shape {array.shape} mismatched"
        except AssertionError as e:
            e.args += (pointer.shape, array.shape)
            raise
        print("Initialize PyTorch weight {}".format(name))
        pointer.data = torch.from_numpy(array)
    for name, shape in init_vars:
        array = tf.train.load_variable(tf_path, name)
        names.append(name)
        arrays.append(array)

sta_name_pos = 0
if device != 'cpu':
    if len(device_ids)>1:
        model = nn.DataParallel(model,device_ids=device_ids)
        sta_name_pos = 1
        
    print('device:', device)
    model.to(device)


if args['strategy'] == 'exBERT':
    if args['train_extension_only']:
        for ii,item in enumerate(model.named_parameters()):
            item[1].requires_grad=False
            if 'ADD' in item[0]:
                item[1].requires_grad = True
            if 'pool' in item[0]:
                item[1].requires_grad=True
            if item[0].split('.')[sta_name_pos]!='bert':
                item[1].requires_grad=True


print('The following part of model is goinig to be trained:')
for ii, item in enumerate(model.named_parameters()):
    if item[1].requires_grad:
        print(item[0])


lr = args['learning_rate']
param_optimizer = list(model.named_parameters())
param_optimizer = [n for n in param_optimizer if 'pooler' not in n[0]]
no_decay = ['bias', 'LayerNorm.bias', 'LayerNorm.weight']
optimizer_grouped_parameters = [
    {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)], 'weight_decay': 0.01},
    {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)], 'weight_decay': 0.0}
    ]



def load_data(data_path,tar_id, sep_range, train_p , random_seed, val_p, load_all = False): #val_p = 1000
    Train_Data = []
    Val_Data = []
    Train_Label = np.array([])
    Val_Label = np.array([])
    # fns = glob.glob(data_path)
    # print('fns', fns)
    # for ii in range(len(fns)):
    print('loading data: ', data_path)
    with open(data_path,'rb') as f:
        temp = pickle.load(f)
        
        print('all data', len(temp[0])) #debug
        print('all data', len(temp[1])) #debug
        
        temp_tl = np.zeros(len(temp[0])*2-val_p*2)
        temp_tl[int(len(temp_tl)/2):] = 1
        temp_vl = np.zeros(val_p*2)
        temp_vl[int(len(temp_vl)/2):] = 1
    Train_Data = temp[0][:-val_p]
    Train_Data = temp[1][:-val_p]
    Val_Data = temp[0][-val_p:]
    Val_Data = temp[1][-val_p:]
    Train_Label = np.concatenate([Train_Label,temp_tl])
    Val_Label = np.concatenate([Val_Label,temp_vl])

    print('shuffle data')
    print('len(Train_Data)', len(Train_Data)) #debug
    print('len(Val_Data)', len(Val_Data)) #debug
    random.Random(random_seed).shuffle(Train_Data)
    random.Random(random_seed).shuffle(Val_Data)
    random.Random(random_seed).shuffle(Train_Label)
    random.Random(random_seed).shuffle(Val_Label)
    Train_Data = Train_Data[:int(train_p)]
    Train_Label = Train_Label[:int(train_p)]
    if load_all:
        return Train_Data,Train_Label,Val_Data,Val_Label
    else:
        Train_Data = Train_Data[tar_id*sep_range:(1+tar_id)*sep_range]
        Train_Label = Train_Label[tar_id*sep_range:(1+tar_id)*sep_range]
        return Train_Data,Train_Label,Val_Data,Val_Label

Train_Data,Train_Label,Val_Data,Val_Label = load_data( args['datat_path'] ,-1,-1, args['train_p'], 0, args['val_p'], load_all=True) 
print('done data preparation')
print('data number: '+str(len(Train_Data)))
print('Val_Data', len(Val_Data))

num_epoc = args['epochs']
batch_size = args['batchsize']
longest_sentence = args['longest_sentence']
total_batch_num = int(np.ceil(len(Train_Data)/batch_size))
optimizer = BertAdam(optimizer_grouped_parameters,lr=lr, warmup=args['warmup'], t_total=total_batch_num)
sep_range = int(total_batch_num/args['sep'])
all_data_num = sep_range*batch_size*args['sep']

train_los_table = np.zeros((num_epoc,sep_range*args['sep']))
val_los_table = np.zeros((num_epoc,sep_range*args['sep']))
best_loss = float('inf')

def process_batch(INPUT, is_train = True):
    # print('-----input----->', INPUT) # debug
    # print('-----len,input----->', len(INPUT)) # debug

    if is_train:
        model.train()
        optimizer.zero_grad()
    Input_ids = t.tensor(INPUT[0]).long().to(device)
    Token_type_ids = t.tensor(INPUT[1]).long().to(device)
    Attention_mask = t.tensor(INPUT[2]).long().to(device)
    Masked_lm_labels = t.tensor(INPUT[3]).long().to(device)
    Next_sentence_label = t.tensor(INPUT[4]).long().to(device)
    loss1 = model(Input_ids,
          token_type_ids = Token_type_ids,
          attention_mask = Attention_mask,
          masked_lm_labels = Masked_lm_labels,
          next_sentence_label = Next_sentence_label
         )
    # print('=======>', loss1) # debug
    # print('======item=>', loss1.item()) # debug
    # print('======type=>', type(loss1)) # debug
    if is_train:
        loss1.unsqueeze(0).backward() #loss1.sum()
        optimizer.step()
        optimizer.zero_grad()
    return loss1.item() #loss1.sum().data


# save_id = 0
print_every_ndata = int(all_data_num/batch_size)##/200 ##output log every 0.5% of data of an epoch is processed
print('------>all_data_num', all_data_num) #debug
print('------>batch_size', batch_size) #debug
print('------>print_every_ndata', print_every_ndata) #debug

print("num_epoc:", num_epoc)

train_epoch_losses = []
val_epoch_losses = []


for epoc in range(num_epoc):
    print('------------------------------>epoc', epoc+1) # debug
    t2 = time.time()
    train_loss = 0  
    val_loss = 0   
     
    train_batch_losses = []
    val_batch_losses = []

    for sep_data_id in range(args['sep']):
        Train_Data,Train_Label,Val_Data,Val_Label = load_data(args['datat_path'],sep_data_id,sep_range*batch_size, args['train_p'], epoc, args['val_p'])
        
        for batch_ind in tqdm(range(int(np.ceil(len(Train_Data)/batch_size)))):
            INPUT = tok.prepare_batch(Train_Data[batch_size*batch_ind:batch_size*(batch_ind+1)],
                                    Train_Label[batch_size*batch_ind:batch_size*(batch_ind+1)],
                                        batch_size=batch_size, longest_sentence=args['longest_sentence'])
            
            # # print("Number of elements in the INPUT tuple:", len(INPUT)) #debug
            # for element in INPUT: #debug
            #     print("Size of an element in INPUT using .shape attribute:", element.shape) #debug
            # print("Size of tensor using .shape attribute:", INPUT.shape) #debug

            print('-------') #debug
            print('Train', len(Train_Data)) #debug
            print('Val', len(Val_Data)) #debug
            
            train_log = process_batch(INPUT)
            print('batch_ind+sep_data_id*sep_range', batch_ind+sep_data_id*sep_range)
            train_los_table[epoc,batch_ind+sep_data_id*sep_range] = train_log
            train_loss += train_log #/ print_every_ndata / batch_size  # Accumulate the loss
            train_batch_losses.append(train_loss)

            print('--------------->epoc', epoc+1) # debug
            print('---------> ', batch_ind) #debug
        
            print(f"Train Epoch: {epoc} [{batch_ind * batch_size + sep_data_id * sep_range * batch_size}/{all_data_num} ({100. * (batch_ind * batch_size + sep_data_id * sep_range * batch_size) / all_data_num:.0f}%)]\ttrain_Loss: {train_loss/print_every_ndata/batch_size:.10f}\tval_Loss: {val_loss/print_every_ndata/batch_size:.10f} time: {time.time() - t2:.4f}\tlr: {optimizer.get_lr()[0]:.10f}")

            train_loss = 0
        
        train_epoch_losses.append(train_batch_losses)       

    
    model.eval()
    val_loss = 0
    
    with t.no_grad():
        for batch_ind in range(int(np.ceil(len(Val_Data)/batch_size))):
            INPUT = tok.prepare_batch(Val_Data[batch_size*batch_ind:batch_size*(batch_ind+1)],
                                    Val_Label[batch_size*batch_ind:batch_size*(batch_ind+1)],
                                    batch_size=batch_size, longest_sentence=args['longest_sentence'])
            val_log = process_batch(INPUT, is_train=False)
            # val_los_table[epoc,batch_ind+sep_data_id*sep_range] = val_log
            val_loss += val_log # / print_every_ndata / batch_size  # Accumulate the loss
            val_batch_losses.append(val_loss)
    
        print('what is val_loss', val_loss)
        val_epoch_losses.append(val_loss)
    
    if val_loss < best_loss:
        # t.save({'epoch':epoc,
        #         'model_state_dict': model.state_dict(),
        #         'optimizer_state_dict': optimizer.state_dict(),
        #         'loss': val_loss}, './results/checkpoint/' +args['strategy']+'e' + str(args['epochs']) +  '_b' + str(args['batchsize']) + '_lr' + str(args['learning_rate']))
        t.save(model.state_dict(),args['save_path']+'/Best_stat_dic_'+args['strategy']+'e' + args['epochs'] +  '_b' + args['batchsize'] + '_lr' + args['learning_rate']+'.pth')
        best_loss = val_loss                     
        t.save(model.state_dict())
# dictionary    
data = {
    'Epoch': list(range(1, num_epoc + 1)),
    'Epoch_TL': train_epoch_losses,
    'Epoch_VL': val_epoch_losses,
    'Train_Losses': train_batch_losses,
    'Val_Losses': val_batch_losses, 
    'Train_Loss_Table': train_los_table, 
    'Val_Loss_Table': val_los_table, 
    'args': args
}

# Save the data dictionary to a pickle file
with open(args['save_path'] + '/losses_' + 'e' + str(args['epochs'])+  '_b' + str(args['batchsize']) + '_lr' + str(args['learning_rate']) + '.pkl', 'wb') as f:
    pickle.dump(data, f)