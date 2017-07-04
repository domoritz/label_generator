---
title: 'Text detection in screen images with a Convolutional Neural Network'
tags:
  - deep learning
  - visualization
  - text detection
authors:
 - name: Dominik Moritz
   orcid: 0000-0002-3110-1053
   affiliation: 1
affiliations:
 - name: University of Washington
   index: 1
date: 9 March 2017
bibliography: paper.bib
---

# Summary

The repository contains a set of scripts to implement text detection from screen images.
The idea is that we use a Convolutional Neural Network (CNN) [@le1990handwritten] to predict a heatmap of the probability of text in an image.
The network outputs a heatmap for text with 64 × 64 pixels and is implemented in Darknet [@darknet13].
To train the network, we use a set of pairs of images and training labels.
We obtain the training data by extracting figures with embedded text from research papers in PDF form and generated pixel masks from them.

With the code, we also provide a dataset of around 500K labeled images extracted from 1M papers from arXiv and the ACL anthology.

# References
