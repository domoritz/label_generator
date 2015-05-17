# Label Generator

Generates labeled training data fro text detector. The input files (json and png) are generated by [pdffigures](http://pdffigures.allenai.org/).


## Usage

* Set up your access and private key for S3
* Compile pdffigures by running `make -C pdffigures DEBUG=0`
* Get a list of all papers
  * `aws s3 --region=us-west-2 ls s3://escience.washington.edu.viziometrics/pdfs/ | awk '{ print $4 }' > paper_list.txt`
    (for testing: `aws s3 ls escience.washington.edu.viziometrics/test/pdf/ | awk '{ print $4 }' > paper_list.txt`)
  * or locally `ls ~/Downloads/papers | cat > paper_list.txt`
* If you use S3, create a ramdisk to speed up file operations.
```
mkdir -p /tmp/ram
sudo mount -t tmpfs -o size=2G tmpfs /tmp/ram/
```
* Run in parallel `cat paper_list.txt | parallel --no-run-if-empty --bar -j 2% --joblog /tmp/par.log python main.py read-s3 escience.washington.edu.viziometrics test/pdf/{} test`

### Resume parallel jobs

Add `--resume` or `--resume-failed` to the command.

### Kill if one fails

`--halt 1`

### Monitor progress

`tail -f /tmp/par.log`


## Requirements

Install OpenCV with python support. Also install freetype, ghostscript, and imagemagic.

## AWS instructions

```
sudo apt-get update
sudo apt-get install python-opencv git ghostscript python-pip libfreetype6 git

git clone https://github.com/domoritz/label_generator.git
cd label_generator
sudo pip install -r requirements.txt
git submodule init
git submodule update

sudo apt-get install libpoppler-dev libleptonica-dev pkg-config

sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
sudo apt-get install g++-4.9

make -C pdffigures DEBUG=0 CC='g++-4.9 -std=c++11'
```


## Try

### Local

`python main.py read testdata/paper.pdf /tmp/test`

### S3

`python main.py read-s3 escience.washington.edu.viziometrics test/pdf/C08-1092.pdf test/ --debug`
