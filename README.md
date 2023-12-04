# [exBERT] Leveraging Large Language Model with Domain Adaption: Enhancing Community Directories with Deep Learning Text Summarization for Machine-Readable Cataloging (MARC) Standard Description Notes

This project is a part of the Master of AI and Machine Learning Research.  Other projects can be found at the [main GitHub repo](https://github.com/camillekokoko/exBERTSum). Presentation can be found at the [youtube link](https://www.youtube.com/watch?v=6KChrujZ3_4)

#### -- Project Status: Active [Active, On-Hold, Completed]

## Project Intro/Objective
The purpose of this project is to build a system utilizing Natural Language Processing (NLP) to generate informative summaries from community's directories in South Australia, accompanied by machine-readable cataloging in adherence to the MARC standard's description notes (Library of Congress 2023).

### Partner
* [SACommunity](https://sacommunity.org/)

### Methods Used
* Generative AI
* Finetune Large Language Models 
* Pretrain Transformer BERT
* Natural Language Processing
* Data Visualization
* etc.

### Technologies
* Python
* Pandas, jupyter
* Pytorch
* Docker
* MySql
* YAML
* JSON
* etc. 

## Project Description (to be completed)
(Provide more detailed overview of the project.  Talk a bit about your data sources and what questions and hypothesis you are exploring. What specific data analysis/visualization and modelling work are you using to solve the problem? What blockers and challenges are you facing?  Feel free to number or bullet point things here)

## Needs of this project

- frontend developers
- data exploration/descriptive statistics
- data processing/cleaning
- statistical modeling
- writeup/reporting
- etc. (be as specific as possible)

## Getting Started (to be completed)

1. Clone this repo 
2. Raw Data is being kept [here](Repo folder containing raw data) within this repo.
3. Data processing/transformation scripts are being kept [here](Repo folder containing data processing scripts/notebooks)
4. Command Scripts are being kept [here]()

## Option 1: Run command script
In command line:

    ./scripts/command_c/auto_run_Cs1_e2_b32_lr1e3.sh ;
    ./scripts/command_c/auto_run_Cs1_e2_b32_lr1e4.sh ;
    ./scripts/command_c/auto_run_Cs1_e2_b32_lr1e5.sh ;
    ./scripts/command_c/auto_run_Cs1_e2_b32_lr1e6.sh ;

## Option 2: Pre-train an exBERT model 
In command line:

    python Pretraining.py \
      -e 1 \
      -b 16 \
      -sp ./results/checkpoint\
      -dv -1 \
      -lr 1e-04 \
      -str exBERT \
      -config ./config/bert_config.json ./config/bert_config_ex_s3.json \
      -vocab ./data/interim/custom_bert_vocab.txt \
      -pm_p ./config/pytorch_model.bin \
      -dp ./data/interim/custom_bert_data_open.pkl \
      -ls 128 \
      -wp 0.5 \
      -t_ex_only "" \
      -train_p 736 \
      -val_p 352
see [AWS_EC2_Docker](https://github.com/camillekokoko/AWS_EC2_Docker) for deployment

## Reference

**[exBERT: Extending Pre-trained Models with Domain-specific Vocabulary Under Constrained Training Resources](https://aclanthology.org/2020.findings-emnlp.129) 

**[github repo](https://github.com/cgmhaicenter/exBERT)**

<<<<<<< HEAD
#summarization
|Models | Rouge-1 | Rouge-2 | Rouge-L |
|-------|---------|---------|---------|
|Bert Ext  | 40      | 40      | 40      |
|exBert Open Ext| 40      | 40      | 40      |
|exBert Combined Ext | 40      | 40      | 40      |
# nlp-summarization-exbert
# nlp-summarization-exbert
=======
>>>>>>> bd59a987d90f242a5442acf0e8fcd1727ed66a88
