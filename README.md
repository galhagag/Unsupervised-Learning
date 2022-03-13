# Unsupervised-Learning
Unsupervised Learning: Comparison of Clustering and Dimension Reduction Techniques}

## Abstract
In the field of data mining, clustering is one of the major issues. The goal of this unsupervised
machine learning technique is to find similarities within the data points and group similar data
points together. Those data points which weren’t labeled in advance go through a data labeling
process. Furthermore, we can remove in advance, before clustering, some of the categories and refer
to them as external variables. This can help us study the link between the categories removed to all
other categories in the data. For example, if we make a survey of leisure activity in the population,
we can remove the category of ”gender”, and after clustering the remaining categories, we can
analyze the link between leisure activities preferred by men to those preferred by women. This
paper covers some unsupervised methods and statistics exams in order to analyze the US Census
Data. The US Census Data is categorical data with 68 categories. At first, we’re removing four
columns – those will be referred to as external variables. We performed multiple corresponding
analysis in order to reduce its dimension and project it to a space in R
10 with numeric values where
we can use cluster methods with a reasonable computing time. After the conversion, we compared
the following methods to cluster the data: K-means, Gaussian mixture model, Agglomerative
clustering, and Spectral clustering. We used different methods to determine the optimal number of
clusters and tuned each algorithm hyperparameters to best fit the data and the external variables.
We used DBSCAN and KNN to find anomalous data points in the data and examined whether they
are associated with any of the external variables. Finally, we projected the data into 2 dimensions
using several techniques in order to visualize data and the clusters. The main conclusion of our
study is that in order to achieve good results, the clustering task needs to be divided into several
steps where each step is based or tied to the previous ones. Each step may include different
methods fitted to the relevant data analyzed, and the conclusion conducted along the way must
be statistically verified. This work was implemented using Python scripts and external libraries.

The data set is available at https://archive.ics.uci.edu/ml/datasets/US+Census+Data+%281990%29
