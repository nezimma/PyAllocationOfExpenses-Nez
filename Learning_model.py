import matplotlib.pyplot as plt
import shutil
import string
import tensorflow
from tensorflow.keras import layers
from tensorflow.keras import losses
import pandas as pd

df = pd.read_csv('DatasetK.csv', sep='|')
# for i in df:
    
