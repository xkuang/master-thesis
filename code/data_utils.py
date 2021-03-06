
# coding: utf-8

# In[1]:


from gensim.models import KeyedVectors
from gensim.models.wrappers import FastText
import numpy as np
import random
import logging

random.seed(0)
logger = logging.getLogger(__name__)


# In[43]:


def read_file_to_lines(path, max_lines):
    logger.info("reading {} into lines...".format(path))
    with open(path, encoding="utf-8") as file_handler:
        lines = file_handler.read().split("\n")[:max_lines]
    
    return lines

def load_embedding_weights(path, words, limit=None):
    """
    Loads pretrained embedding weights from given path
    
    Args:
        path: Path to fast text embeddings
        words: dictionary of words (e.g. {0: "PAD", 1: "cat", 2: "dog"}), word on index 0 is considered to be PADDING and its weights are set to 0
    
    Returns:
        list of weights in the same order as are words
    """
    logger.debug("load_embedding_weights from {} for {} words"
                 .format(path, len(words)))
    
    # don't know how to limit size of vocabulary with FastText
    # loading the whole model takes too much time
    # TODO use FastText for final version, because it can generate
    # vectors for OOV words from ngrams
    # model = FastText.load_fasttext_format(path)
    
    model = KeyedVectors.load_word2vec_format(path, limit=limit)
    
    #model.get_keras_embedding()
    
    # Get dimension
    dim = model.vector_size
    
    logger.info("getting embedding weights for each word")
    weights = []
    for index, word in words.items():    
        if index == 0:
            # Set zero weight for padding symbol
            weight = np.zeros(dim)
        elif word in model:
            # https://radimrehurek.com/gensim/models/wrappers/fasttext.html
            # The word can be out-of-vocabulary as long as ngrams for the word are present. For words with all ngrams absent, a KeyError is raised.
            weight = model[word]
        else:
            logging.warning("out of vocabulary word: {}".format(word))
            
            # Init random weights for out of vocabulary word        
            # TODO are the values in range (-1, 1)?
            weight = np.random.uniform(low=-1.0, high=1.0, size=(dim))
            
            
            # TODO in final version change to fastText model
            # weight = model.seeded_vector(random.random())
            # https://www.quora.com/How-does-fastText-output-a-vector-for-a-word-that-is-not-in-the-pre-trained-model

        weights.append(weight)
    
    logging.info("weights loaded")
    return np.asarray(weights)

def get_bucket_ix(seq_length, bucket_range):
    return seq_length // bucket_range + (1 if seq_length % bucket_range != 0 else 0)

def split_to_buckets(X_sequences, y_sequences, bucket_range=3, X_max_len=None, y_max_len=None, bucket_min_size=10):
    """
    Split list of sequences to list of buckets where each bucket is a list of word sequences
    with similar length (based on the bucket_range size e.g. with bucket_size=3 sequences with length 1-3 falls in same bucket)
    
    Args:
        X_sequences: one list of sequences
        y_sequences: another list of sequences
        bucket_range: size of one bucket (how big range of sequence lengths should fall into one bucket)
        X_max_len: optional max length of X sequences
        y_max_len: optional max length of y sequences
        bucket_min_size: minimal size of a bucket. If its lower, than the bucket gets merged with other bucket
    
    Returns:
        dict of buckets each with the Y and y list of similary long sequences and their max length
    """
    logger.info("splitting sequences to buckets with range {}".format(bucket_range))
    
    assert len(X_sequences) == len(y_sequences)
    
    if not X_max_len:
        X_max_len = max(len(seq) for seq in X_sequences)
    if not y_max_len:
        y_max_len = max(len(seq) for seq in y_sequences)        
    
    all_max_len = max(X_max_len, y_max_len)
    
    logger.debug("x_max_len = {}, y_max_len = {}".format(X_max_len, y_max_len))
    
    num_buckets = get_bucket_ix(all_max_len, bucket_range)

    buckets = {}
    
    logger.debug("num buckets = {}".format(num_buckets))
    
    for i in range(len(X_sequences)):
        X_seq = X_sequences[i]
        y_seq = y_sequences[i]
        X_len = len(X_seq)
        y_len = len(y_seq)
        
        max_len = max(X_len, y_len)
        bucket = get_bucket_ix(max_len, bucket_range)
        
        if bucket not in buckets:
            buckets[bucket] = {"X_word_seq": [], "y_word_seq": [], "X_max_seq_len": 0, "y_max_seq_len": 0}
        
        buckets[bucket]["X_word_seq"].append(X_seq)
        buckets[bucket]["y_word_seq"].append(y_seq)
        buckets[bucket]["X_max_seq_len"] = max(buckets[bucket]["X_max_seq_len"], X_len)
        buckets[bucket]["y_max_seq_len"] = max(buckets[bucket]["y_max_seq_len"], y_len)
    
    # merge buckets lower then bucket_min_size for optimization
    # so we don't run fit method over really small input lists
    logger.debug("bucket_min_size={}".format(bucket_min_size))
    delete_ixs = []
    for ix in buckets.keys():
        bucket = buckets[ix]
        if len(bucket["X_word_seq"]) < bucket_min_size:
            if ix < len(buckets.keys()):
                merge_ix = ix + 1
            else:
                merge_ix = ix - 1
                buckets[merge_ix]["X_max_seq_len"] = bucket["X_max_seq_len"]
                buckets[merge_ix]["y_max_seq_len"] = bucket["y_max_seq_len"]
            
            logger.info("bucket {} is too small, merging with bucket {}".format(ix, merge_ix))            
            delete_ixs.append(ix)
            
            buckets[merge_ix]["X_word_seq"] +=bucket["X_word_seq"]
            buckets[merge_ix]["y_word_seq"] +=bucket["y_word_seq"]
    
    for ix in delete_ixs:
        del buckets[ix]
    
    return buckets


# In[40]:


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     weights = load_embedding_weights("G:/Clouds/DPbigFiles/facebookVectors/facebookPretrained-wiki.cs.vec",
#                            {0:"PAD", 1:"kostka", 2:"pes", 3:"UNK"}, limit=1000)
    
    x_word_seq = [
        ["1"],
        ["1", "2"],
        ["1", "2", "3"],
        ["1", "2", "3", "4"],
        ["1", "2", "3", "4", "5"],
        ["1", "2", "3", "4", "5"],
        ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    ]
    
    y_word_seq = [
        ["1"],
        ["1", "2"],
        ["1", "2"],
        ["1", "2", "3", "4"],
        ["1", "2", "3", "4", "5"],
        ["1", "2", "3", "4", "5", "6", "7"],
        ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    ]
    buckets = split_to_buckets(x_word_seq, y_word_seq, 2, bucket_min_size=2)
    
    for bucket in buckets:
        print(bucket, buckets[bucket])

