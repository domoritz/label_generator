# Text detection in screen images with a Convolutional Neural Network

The repository contains a set of scripts to implement text detection from screen images. The idea is that we use a Convolutional Neural Network (CNN) to predict a heatmap of the probability of text in an image. But before we can predict anything, we need to train the network with a a set of pairs of images and training labels. We obtain the training data by extracting figures with embedded text from research papers.


## Requirements

Install OpenCV with python support. Also install freetype, ghostscript, imagemagic, and tesseract.

## Generate training data

You can run this locally or on a server. I tested every script locally on a mac without any problems. Below are instructions for Linux.

The scripts use [pdffigures](http://pdffigures.allenai.org/) to generate a JSON file that describes each figure in a paper.

### AWS instructions

These are the steps I had to run to generate the training data an EC2 machines on AWS. The execution is embarrassingly parallel and thus runs reasonably fast (a few hours to a day or two for a million papers).

```sh
# use tmux (maybe with attach)
tmux

sudo apt-get update
sudo apt-get install git python-pip python-opencv ghostscript libmagickwand-dev libfreetype6 git parallel

git clone https://github.com/domoritz/label_generator.git
cd label_generator
sudo pip install -r requirements.txt
git submodule init
git submodule update

sudo apt-get install libpoppler-dev libleptonica-dev pkg-config

# we need gcc 4.9
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
sudo apt-get install g++-4.9

# copmpile pdffigures
make -C pdffigures DEBUG=0 CC='g++-4.9 -std=c++11'

# at this point, you probably need to make a copy of the config file and update it
cp config_sample.py config.py
vim config.py

# test with one file
python label_gen.py read-s3 escience.washington.edu.viziometrics acl_anthology/pdf/C08-1099.pdf acl_anthology

# get list of documents to process
aws s3 --region=us-west-2 ls s3://escience.washington.edu.viziometrics/acl_anthology/pdf/ | awk '{ print $4 }' > acl_papers.txt

# now run for real
parallel --resume -j +6 --no-run-if-empty --eta --joblog /tmp/par.log python label_gen.py read-s3 escience.washington.edu.viziometrics acl_anthology/pdf/{} escience.washington.edu.viziometrics acl_anthology --dbg-image :::: acl_papers.txt

# monitor progress
tail -f /tmp/par.log

# find bad labels
python find_bad.py read-s3 escience.washington.edu.viziometrics acl_anthology/json > anthology_bad.txt
# you probably want to use this file to delete bad labels before you use it to train the CNN
# Use: parallel rm -f data/{}-label.png :::: anthology_bad.txt

# run find bad in parallel
seq {0,19} | parallel -j 20 --eta python find_bad.py read-s3 escience.washington.edu.viziometrics arxiv/json --chunk={} --of=20 '>' arxiv_bad_{}.txt
cat arxiv_bad_*.txt > arxiv_bad.txt

# at this point you may want to upload the file with bad labels back to S3
```

### FAQ for common error messages

These are some common errors I have experienced.

**I don't see my output** Try `--debug` and make sure that you have the correct folders set up if you use S3.

**Failed to initialize libdc1394** `sudo ln /dev/null /dev/raw1394` https://stackoverflow.com/questions/12689304/ctypes-error-libdc1394-error-failed-to-initialize-libdc1394

### Try the figure extraction

#### Local

`python label_gen.py read testdata/paper.pdf /tmp/test --dbg-image --debug`

#### With data from S3

`python label_gen.py read-s3 escience.washington.edu.viziometrics test/pdf/C08-1092.pdf test/ --dbg-image --debug`


## Train the neural network

I used a different machine for training the network because AWS doesn't have good graphics cards.

To test the prediction

## Predict where text is and find text areas



