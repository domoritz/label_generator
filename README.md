# Text detection in screen images with a Convolutional Neural Network [![theoj](http://joss.theoj.org/papers/d2821f933fc95337202393e84189f4d9/status.svg)](http://joss.theoj.org/papers/d2821f933fc95337202393e84189f4d9) [![Build Status](https://travis-ci.org/domoritz/label_generator.svg?branch=master)](https://travis-ci.org/domoritz/label_generator)

**Note: This was a class project where I wanted to learn about neural networks. If you want to do text detection in images, I suggest that you use something like [this approach](http://www.math.tau.ac.il/~turkel/imagepapers/text_detection.pdf).**

The repository contains a set of scripts to implement text detection from screen images. The idea is that we use a Convolutional Neural Network (CNN) to predict a heatmap of the probability of text in an image. But before we can predict anything, we need to train the network with a a set of pairs of images and training labels. We obtain the training data by extracting figures with embedded text from research papers.

**This is a very involved process and you may want to use the labels that I already generated (you are welcome). We have around 500K good labels extracted from around 1M papers from arXiv and the ACL anthology.**

PDF files, extracted figures and labels are in an S3 bucket at `s3://escience.washington.edu.viziometrics`. The PDF files for arXiv (extracted from [arXiv bulk access](http://arxiv.org/help/bulk_data_s3)) are in a separate bucket at `s3://arxiv-tars-pdfs`. The buckets have [requester pays](https://docs.aws.amazon.com/en_us/console/s3/requesterpaysbucket) enabled.

Please cite [the paper for this repo](https://www.theoj.org/joss-papers/joss.00235/10.21105.joss.00235.pdf) as

```bib
@article{Moritz2017,
  doi = {10.21105/joss.00235},
  url = {https://doi.org/10.21105/joss.00235},
  year = {2017},
  month = jul,
  publisher = {The Open Journal},
  volume = {2},
  number = {15},
  pages = {235},
  author = {Dominik Moritz},
  title = {Text detection in screen images with a Convolutional Neural Network},
  journal = {The Journal of Open Source Software}
}
```

## Requirements

Install OpenCV with python support. Also install scipy, matplotlib, and numpy for python (either through pip or apt). Also install freetype, ghostscript, imagemagic, and tesseract. Please check the compatible versions of [pdffigures](https://github.com/allenai/pdffigures) with your OS.

## Generate training data

You can run this locally or on a server. I tested every script locally on a mac without any problems. Below are instructions for Linux.

The scripts use [pdffigures](http://pdffigures.allenai.org/) to generate a JSON file that describes each figure in a paper.

### AWS instructions

These are the steps I had to run to generate the training data an EC2 machines on AWS. The execution is embarrassingly parallel and thus runs reasonably fast (a few hours to a day or two for a million papers). At the time of writing, I ran this on Ubuntu 14.04, but later version may work as well with some small modifications.

The commands below are what I used to extract the images and generate the labels. As described above, you don't need to rerun this unless you want to use different papers than the ones I already extracted figures from (see above). If you want to run the code, you need to change the output S3 bucket to a bucket that you have write access to.

```sh
# use tmux (maybe with attach)
tmux

sudo apt-get update
sudo apt-get install git python-pip python-opencv python-numpy python-scipy python-matplotlib ghostscript libmagickwand-dev libfreetype6 parallel

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

# compile pdffigures
make -C pdffigures DEBUG=0 CC='g++-4.9 -std=c++11'

# at this point, you probably need to make a copy of the config file and update it
cp config_sample.py config.py
vim config.py

# test with one file
python label_gen.py read-s3 escience.washington.edu.viziometrics acl_anthology/pdf/C08-1099.pdf escience.washington.edu.viziometrics acl_anthology

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

**ImportError: MagickWand shared library not found.** See https://github.com/dahlia/wand/issues/141

### Try the figure extraction

#### Local

`python label_gen.py read testdata/paper.pdf /tmp/test --dbg-image --debug`

#### With data from S3

`python label_gen.py read-s3 escience.washington.edu.viziometrics test/pdf/C08-1092.pdf test/ --dbg-image --debug`


## Train the neural network

I used a different machine for training the network because AWS doesn't have good graphics cards.

You can use any CNN to get the prediction but I use [pjreddie/darknet](https://github.com/pjreddie/darknet). My fork is at [domoritz/darknet](https://github.com/domoritz/darknet) and a submodule of this repo.

To train the network, you need to put all figures and labels into one directory. Then generate a  file called `train.list` in `/data`. You can generate this file with `ls . | grep -v -- "-label.png" | awk '{print "PATH_TO_FILES/"$1}' > ../all.list` in the directory with all the images. Then split the file into training and test data.

Then train the network with `./darknet writing train cfg/writing.cfg`. This will generate a weight file every now and then. If for some reason some files are missing labels, use a python script like this to filter out files that don't have labels.

```python
import sys
import os.path

with open(sys.argv[1]) as f:
        for fname in f:
                fname = fname.strip()
                if not os.path.isfile(fname):
                        print fname
                lname = fname[:-4] + "-label.png"
                if not os.path.isfile(lname):
                        print fname
```

## Predict where text is and find text areas

You need a trained network. To test the network, run `echo "PATH_TO_FILES/FIGURE.png" | ./darknet writing test cfg/writing.cfg ../writing_backup/writing_ITER.weights`. If you append `out`, a prediction will be written to `out.png`.

A prediction looks like this

![Red boxes around extracted text](https://raw.githubusercontent.com/domoritz/label_generator/master/screenshots/hep-th0401120-Figure-23-prediction.png)

If you want to test the network on all your test data, use a script like

```bash
for i in `cat $1` ; do
    fname=`basename $i .png`
    echo $i | ./darknet writing test cfg/writing.cfg ../writing_backup/writing_8500.weights PATH_FOR_PREDICTIONS/$fname-predicted
done
```

and run it with your list of training data as the input. This will write all the predictions into a directory. If you feel like moving all your other files (the ground truth, images and such), use a command like `cat test.list | xargs cp -t PATH_FOR_PREDICTIONS`.

Cool, now we have a bunch of images in one directory. Let's find out what the precision and recall are. First, create a list of all the files in the directory with `ls | grep -- "-predicted.png" > _all.list`. Then just run `python rate.py ../predicted/predicted/_all.list`.

After all this work, we can finally generate a prediction, find contours, fit boxes around contours and find text with tesseract. To do so, run `python predict.py PREDICTION FIGURE_IMAGE --debug`. You may see something like

![Red boxes around extracted text](https://raw.githubusercontent.com/domoritz/label_generator/master/screenshots/text-debug.png)

## Support

Please ask questions and files issues [on GitHub](https://github.com/domoritz/label_generator/issues/new).

## Contribute

Contributions are welcome. Development happens on GitHub at [domoritz/label_generator](https://github.com/domoritz/label_generator). When sending a pull request, please compare the output of `python label_gen.py read testdata/paper.pdf /tmp/test` with the images in [`testoutput`](https://github.com/domoritz/label_generator/tree/master/testoutput).
