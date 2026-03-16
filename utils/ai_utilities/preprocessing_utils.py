"""
预处理工具模块

提供AI模型数据预处理的工具函数，包括文本、图像、数值、分类数据的预处理，
以及特征工程、数据清洗、数据增强等功能。
"""

import re
import string
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from collections import Counter
import hashlib
import json
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder,
    OneHotEncoder, OrdinalEncoder, KBinsDiscretizer, PowerTransformer,
    QuantileTransformer, PolynomialFeatures, FunctionTransformer
)
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer, HashingVectorizer
from sklearn.feature_selection import (
    SelectKBest, SelectPercentile, RFE, RFECV,
    chi2, f_classif, f_regression, mutual_info_classif, mutual_info_regression
)
from sklearn.decomposition import PCA, TruncatedSVD, NMF, FactorAnalysis, FastICA
from sklearn.manifold import TSNE, Isomap
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer, KNNImputer
from imblearn.over_sampling import SMOTE, ADASYN, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler, NearMiss
import cv2
from PIL import Image, ImageEnhance, ImageFilter
import librosa
import soundfile as sf


class TextPreprocessor:
    """文本预处理器"""
    
    def __init__(self, lowercase: bool = True, remove_punctuation: bool = True,
                 remove_numbers: bool = False, remove_stopwords: bool = False,
                 stopwords: Optional[List[str]] = None, language: str = 'english',
                 stemming: bool = False, lemmatization: bool = False,
                 min_word_length: int = 1, max_word_length: int = 100,
                 custom_patterns: Optional[List[Tuple[str, str]]] = None):
        """初始化文本预处理器
        
        Args:
            lowercase: 是否转小写
            remove_punctuation: 是否移除标点符号
            remove_numbers: 是否移除数字
            remove_stopwords: 是否移除停用词
            stopwords: 停用词列表
            language: 语言
            stemming: 是否词干提取
            lemmatization: 是否词形还原
            min_word_length: 最小词长度
            max_word_length: 最大词长度
            custom_patterns: 自定义替换模式 [(pattern, replacement), ...]
        """
        self.lowercase = lowercase
        self.remove_punctuation = remove_punctuation
        self.remove_numbers = remove_numbers
        self.remove_stopwords = remove_stopwords
        self.stopwords = stopwords or self._get_default_stopwords(language)
        self.language = language
        self.stemming = stemming
        self.lemmatization = lemmatization
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
        self.custom_patterns = custom_patterns or []
        
        # 初始化NLP工具
        self._init_nlp_tools()
    
    def _init_nlp_tools(self):
        """初始化NLP工具"""
        if self.stemming:
            try:
                from nltk.stem import PorterStemmer, SnowballStemmer
                if self.language == 'english':
                    self.stemmer = PorterStemmer()
                else:
                    self.stemmer = SnowballStemmer(self.language)
            except ImportError:
                print("nltk not installed, stemming disabled")
                self.stemming = False
        
        if self.lemmatization:
            try:
                from nltk.stem import WordNetLemmatizer
                self.lemmatizer = WordNetLemmatizer()
            except ImportError:
                print("nltk not installed, lemmatization disabled")
                self.lemmatization = False
    
    def _get_default_stopwords(self, language: str) -> List[str]:
        """获取默认停用词"""
        default_stopwords = {
            'english': ['a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
                       'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
                       'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during',
                       'to', 'too', 'very', 'can', 'will', 'just', 'don', "don't", 'should',
                       "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren',
                       "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't",
                       'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't",
                       'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't",
                       'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren',
                       "weren't", 'won', "won't", 'wouldn', "wouldn't"],
            'chinese': ['的', '了', '和', '是', '就', '都', '而', '及', '与', '着',
                       '或', '一个', '没有', '我们', '你们', '他们', '它们', '这个',
                       '那个', '这些', '那些', '这样', '那样', '之', '的', '得'],
            'french': ['le', 'la', 'les', 'de', 'des', 'du', 'et', 'est', 'sont',
                      'dans', 'pour', 'par', 'sur', 'avec', 'ce', 'cet', 'cette',
                      'ces', 'mon', 'ton', 'son', 'notre', 'votre', 'leur',
                      'mes', 'tes', 'ses', 'nos', 'vos', 'leurs'],
            'german': ['der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine',
                      'einer', 'eines', 'einem', 'einen', 'und', 'oder', 'aber',
                      'mit', 'von', 'für', 'auf', 'bei', 'nach', 'aus', 'durch',
                      'über', 'unter', 'zwischen', 'vor', 'hinter', 'neben']
        }
        
        return default_stopwords.get(language.lower(), default_stopwords['english'])
    
    def clean_text(self, text: str) -> str:
        """清理文本
        
        Args:
            text: 输入文本
            
        Returns:
            清理后的文本
        """
        if not isinstance(text, str):
            return ""
        
        # 应用自定义模式
        for pattern, replacement in self.custom_patterns:
            text = re.sub(pattern, replacement, text)
        
        # 转小写
        if self.lowercase:
            text = text.lower()
        
        # 移除标点符号
        if self.remove_punctuation:
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # 移除数字
        if self.remove_numbers:
            text = re.sub(r'\d+', ' ', text)
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """分词
        
        Args:
            text: 输入文本
            
        Returns:
            词列表
        """
        # 简单分词（按空格）
        tokens = text.split()
        
        # 过滤词长度
        tokens = [t for t in tokens if self.min_word_length <= len(t) <= self.max_word_length]
        
        return tokens
    
    def remove_stopwords_from_tokens(self, tokens: List[str]) -> List[str]:
        """从词列表中移除停用词"""
        if not self.remove_stopwords:
            return tokens
        
        return [t for t in tokens if t not in self.stopwords]
    
    def apply_stemming(self, tokens: List[str]) -> List[str]:
        """应用词干提取"""
        if not self.stemming:
            return tokens
        
        return [self.stemmer.stem(t) for t in tokens]
    
    def apply_lemmatization(self, tokens: List[str]) -> List[str]:
        """应用词形还原"""
        if not self.lemmatization:
            return tokens
        
        return [self.lemmatizer.lemmatize(t) for t in tokens]
    
    def preprocess_text(self, text: str) -> str:
        """完整文本预处理（返回字符串）"""
        text = self.clean_text(text)
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords_from_tokens(tokens)
        tokens = self.apply_stemming(tokens)
        tokens = self.apply_lemmatization(tokens)
        
        return ' '.join(tokens)
    
    def preprocess_to_tokens(self, text: str) -> List[str]:
        """完整文本预处理（返回词列表）"""
        text = self.clean_text(text)
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords_from_tokens(tokens)
        tokens = self.apply_stemming(tokens)
        tokens = self.apply_lemmatization(tokens)
        
        return tokens
    
    def batch_preprocess(self, texts: List[str], as_tokens: bool = False) -> List[Union[str, List[str]]]:
        """批量预处理文本
        
        Args:
            texts: 文本列表
            as_tokens: 是否返回词列表
            
        Returns:
            预处理后的文本列表
        """
        if as_tokens:
            return [self.preprocess_to_tokens(t) for t in texts]
        else:
            return [self.preprocess_text(t) for t in texts]
    
    def extract_features(self, texts: List[str]) -> np.ndarray:
        """提取文本特征
        
        Args:
            texts: 文本列表
            
        Returns:
            特征矩阵
        """
        # 使用TF-IDF向量化
        vectorizer = TfidfVectorizer(max_features=1000)
        return vectorizer.fit_transform(texts).toarray()
    
    def get_text_statistics(self, text: str) -> Dict[str, Any]:
        """获取文本统计信息"""
        tokens = self.preprocess_to_tokens(text)
        
        return {
            'length': len(text),
            'word_count': len(tokens),
            'char_count': len(text),
            'unique_words': len(set(tokens)),
            'avg_word_length': np.mean([len(t) for t in tokens]) if tokens else 0,
            'sentence_count': len(re.split(r'[.!?]+', text)) - 1
        }


class ImagePreprocessor:
    """图像预处理器"""
    
    def __init__(self, target_size: Tuple[int, int] = (224, 224),
                 normalize: bool = True, mean: Optional[List[float]] = None,
                 std: Optional[List[float]] = None, grayscale: bool = False,
                 color_mode: str = 'rgb', interpolation: int = cv2.INTER_LINEAR,
                 augment: bool = False, augmentation_config: Optional[Dict] = None):
        """初始化图像预处理器
        
        Args:
            target_size: 目标尺寸 (height, width)
            normalize: 是否归一化
            mean: 均值列表 (用于归一化)
            std: 标准差列表 (用于归一化)
            grayscale: 是否转为灰度图
            color_mode: 颜色模式 ('rgb', 'bgr', 'rgba')
            interpolation: 插值方法
            augment: 是否数据增强
            augmentation_config: 增强配置
        """
        self.target_size = target_size
        self.normalize = normalize
        self.mean = mean or [0.485, 0.456, 0.406]
        self.std = std or [0.229, 0.224, 0.225]
        self.grayscale = grayscale
        self.color_mode = color_mode.lower()
        self.interpolation = interpolation
        self.augment = augment
        self.augmentation_config = augmentation_config or {}
        
        # 验证颜色模式
        if self.color_mode not in ['rgb', 'bgr', 'rgba', 'gray']:
            self.color_mode = 'rgb'
    
    def read_image(self, image_path: str) -> np.ndarray:
        """读取图像
        
        Args:
            image_path: 图像路径
            
        Returns:
            图像数组
        """
        image = cv2.imread(image_path)
        
        if image is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        # 转换颜色空间
        if self.color_mode == 'rgb':
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif self.color_mode == 'gray' or self.grayscale:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if len(image.shape) == 2:
                image = np.expand_dims(image, axis=-1)
        elif self.color_mode == 'rgba':
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)
        
        return image
    
    def resize_image(self, image: np.ndarray) -> np.ndarray:
        """调整图像尺寸
        
        Args:
            image: 输入图像
            
        Returns:
            调整后的图像
        """
        if image.shape[:2] != self.target_size:
            image = cv2.resize(image, (self.target_size[1], self.target_size[0]), 
                              interpolation=self.interpolation)
        
        return image
    
    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """归一化图像
        
        Args:
            image: 输入图像
            
        Returns:
            归一化后的图像
        """
        if not self.normalize:
            return image
        
        image = image.astype(np.float32) / 255.0
        
        # 使用指定均值和标准差
        if len(image.shape) == 3 and image.shape[-1] == len(self.mean):
            for i in range(len(self.mean)):
                image[..., i] = (image[..., i] - self.mean[i]) / self.std[i]
        
        return image
    
    def apply_augmentation(self, image: np.ndarray) -> np.ndarray:
        """应用数据增强
        
        Args:
            image: 输入图像
            
        Returns:
            增强后的图像
        """
        if not self.augment:
            return image
        
        import random
        
        # 随机旋转
        if self.augmentation_config.get('rotation', False):
            angle = random.uniform(-self.augmentation_config.get('rotation_range', 30),
                                  self.augmentation_config.get('rotation_range', 30))
            h, w = image.shape[:2]
            matrix = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
            image = cv2.warpAffine(image, matrix, (w, h))
        
        # 随机翻转
        if self.augmentation_config.get('flip_horizontal', False) and random.random() > 0.5:
            image = cv2.flip(image, 1)
        
        if self.augmentation_config.get('flip_vertical', False) and random.random() > 0.5:
            image = cv2.flip(image, 0)
        
        # 随机裁剪
        if self.augmentation_config.get('crop', False):
            crop_ratio = self.augmentation_config.get('crop_ratio', 0.8)
            h, w = image.shape[:2]
            crop_h = int(h * crop_ratio)
            crop_w = int(w * crop_ratio)
            
            start_h = random.randint(0, h - crop_h)
            start_w = random.randint(0, w - crop_w)
            image = image[start_h:start_h + crop_h, start_w:start_w + crop_w]
            
            # 调整回原尺寸
            image = cv2.resize(image, (w, h), interpolation=self.interpolation)
        
        # 亮度调整
        if self.augmentation_config.get('brightness', False):
            factor = random.uniform(self.augmentation_config.get('brightness_range', 0.8),
                                   self.augmentation_config.get('brightness_range', 1.2))
            image = cv2.convertScaleAbs(image, alpha=factor, beta=0)
        
        return image
    
    def preprocess_image(self, image: Union[str, np.ndarray]) -> np.ndarray:
        """完整图像预处理
        
        Args:
            image: 输入图像（路径或数组）
            
        Returns:
            预处理后的图像
        """
        # 加载图像
        if isinstance(image, str):
            image = self.read_image(image)
        elif isinstance(image, Image.Image):
            image = np.array(image)
        
        # 数据增强
        image = self.apply_augmentation(image)
        
        # 调整尺寸
        image = self.resize_image(image)
        
        # 归一化
        image = self.normalize_image(image)
        
        return image
    
    def batch_preprocess(self, images: List[Union[str, np.ndarray]]) -> np.ndarray:
        """批量预处理图像
        
        Args:
            images: 图像列表
            
        Returns:
            预处理后的图像数组
        """
        processed_images = [self.preprocess_image(img) for img in images]
        return np.array(processed_images)
    
    def extract_features(self, images: List[np.ndarray], 
                        feature_extractor: str = 'hog') -> np.ndarray:
        """提取图像特征
        
        Args:
            images: 图像列表
            feature_extractor: 特征提取器 ('hog', 'histogram', 'lbp')
            
        Returns:
            特征矩阵
        """
        features = []
        
        for img in images:
            if feature_extractor == 'hog':
                # HOG特征
                from skimage.feature import hog
                fd = hog(img, orientations=9, pixels_per_cell=(8, 8),
                        cells_per_block=(2, 2), visualize=False)
                features.append(fd)
            
            elif feature_extractor == 'histogram':
                # 颜色直方图
                hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8],
                                   [0, 256, 0, 256, 0, 256])
                features.append(hist.flatten())
            
            elif feature_extractor == 'lbp':
                # LBP特征
                from skimage.feature import local_binary_pattern
                lbp = local_binary_pattern(img.mean(axis=-1) if img.ndim == 3 else img, 24, 8)
                hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
                features.append(hist)
        
        return np.array(features)


class NumericalPreprocessor:
    """数值预处理器"""
    
    def __init__(self, scaling_method: str = 'standard', 
                 scaling_params: Optional[Dict] = None,
                 outlier_method: Optional[str] = None,
                 outlier_params: Optional[Dict] = None,
                 discretization_method: Optional[str] = None,
                 discretization_params: Optional[Dict] = None):
        """初始化数值预处理器
        
        Args:
            scaling_method: 缩放方法 ('standard', 'minmax', 'robust', 'power', 'quantile', 'none')
            scaling_params: 缩放参数
            outlier_method: 异常值处理方法 ('clip', 'remove', 'winsorize', 'none')
            outlier_params: 异常值处理参数
            discretization_method: 离散化方法 ('kbins', 'quantile', 'none')
            discretization_params: 离散化参数
        """
        self.scaling_method = scaling_method
        self.scaling_params = scaling_params or {}
        self.outlier_method = outlier_method
        self.outlier_params = outlier_params or {}
        self.discretization_method = discretization_method
        self.discretization_params = discretization_params or {}
        
        self.scaler = None
        self.discretizer = None
        self.fitted = False
    
    def _init_scaler(self):
        """初始化缩放器"""
        if self.scaling_method == 'standard':
            self.scaler = StandardScaler(**self.scaling_params)
        elif self.scaling_method == 'minmax':
            self.scaler = MinMaxScaler(**self.scaling_params)
        elif self.scaling_method == 'robust':
            self.scaler = RobustScaler(**self.scaling_params)
        elif self.scaling_method == 'power':
            self.scaler = PowerTransformer(**self.scaling_params)
        elif self.scaling_method == 'quantile':
            self.scaler = QuantileTransformer(**self.scaling_params)
        elif self.scaling_method == 'none':
            self.scaler = FunctionTransformer(lambda x: x)
        else:
            self.scaler = StandardScaler(**self.scaling_params)
    
    def _init_discretizer(self):
        """初始化离散化器"""
        if self.discretization_method == 'kbins':
            self.discretizer = KBinsDiscretizer(**self.discretization_params)
        elif self.discretization_method == 'quantile':
            params = {'n_quantiles': self.discretization_params.get('n_bins', 10)}
            self.discretizer = QuantileTransformer(**params)
        else:
            self.discretizer = None
    
    def _handle_outliers(self, X: np.ndarray) -> np.ndarray:
        """处理异常值"""
        if self.outlier_method == 'clip':
            lower = np.percentile(X, self.outlier_params.get('lower_percentile', 1), axis=0)
            upper = np.percentile(X, self.outlier_params.get('upper_percentile', 99), axis=0)
            return np.clip(X, lower, upper)
        
        elif self.outlier_method == 'remove':
            # 返回掩码，实际移除在外层处理
            return X
        
        elif self.outlier_method == 'winsorize':
            from scipy.stats.mstats import winsorize
            limits = self.outlier_params.get('limits', 0.05)
            return winsorize(X, limits=limits)
        
        return X
    
    def fit(self, X: np.ndarray) -> 'NumericalPreprocessor':
        """拟合并转换数据
        
        Args:
            X: 输入数据
            
        Returns:
            自身
        """
        X = np.array(X).reshape(-1, 1) if X.ndim == 1 else X
        
        # 初始化
        self._init_scaler()
        self._init_discretizer()
        
        # 拟合缩放器
        self.scaler.fit(X)
        
        # 拟合离散化器
        if self.discretizer:
            self.discretizer.fit(X)
        
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """转换数据
        
        Args:
            X: 输入数据
            
        Returns:
            转换后的数据
        """
        if not self.fitted:
            raise ValueError("Preprocessor not fitted yet. Call fit() first.")
        
        X = np.array(X).reshape(-1, 1) if X.ndim == 1 else X
        
        # 处理异常值
        X = self._handle_outliers(X)
        
        # 缩放
        X_scaled = self.scaler.transform(X)
        
        # 离散化
        if self.discretizer:
            X_discrete = self.discretizer.transform(X_scaled)
            return X_discrete
        
        return X_scaled
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """拟合并转换数据"""
        self.fit(X)
        return self.transform(X)
    
    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """逆转换数据"""
        if not self.fitted:
            raise ValueError("Preprocessor not fitted yet. Call fit() first.")
        
        X = np.array(X).reshape(-1, 1) if X.ndim == 1 else X
        
        if self.discretizer:
            # 离散化不可逆，返回缩放后的数据
            return X
        
        return self.scaler.inverse_transform(X)


class CategoricalPreprocessor:
    """分类预处理器"""
    
    def __init__(self, encoding_method: str = 'onehot',
                 encoding_params: Optional[Dict] = None,
                 handle_unknown: str = 'ignore',
                 handle_missing: str = 'error',
                 max_categories: Optional[int] = None):
        """初始化分类预处理器
        
        Args:
            encoding_method: 编码方法 ('onehot', 'label', 'ordinal', 'binary', 'hash', 'count')
            encoding_params: 编码参数
            handle_unknown: 处理未知值的方式 ('ignore', 'error')
            handle_missing: 处理缺失值的方式 ('error', 'as_category', 'fill_with')
            max_categories: 最大类别数
        """
        self.encoding_method = encoding_method
        self.encoding_params = encoding_params or {}
        self.handle_unknown = handle_unknown
        self.handle_missing = handle_missing
        self.max_categories = max_categories
        
        self.encoder = None
        self.categories_ = None
        self.fitted = False
    
    def _init_encoder(self):
        """初始化编码器"""
        if self.encoding_method == 'onehot':
            self.encoder = OneHotEncoder(
                handle_unknown=self.handle_unknown,
                sparse_output=False,
                **self.encoding_params
            )
        elif self.encoding_method == 'label':
            self.encoder = LabelEncoder()
        elif self.encoding_method == 'ordinal':
            self.encoder = OrdinalEncoder(
                handle_unknown='use_encoded_value' if self.handle_unknown == 'ignore' else 'error',
                unknown_value=-1,
                **self.encoding_params
            )
        elif self.encoding_method == 'binary':
            try:
                from category_encoders import BinaryEncoder
                self.encoder = BinaryEncoder(**self.encoding_params)
            except ImportError:
                raise ImportError("BinaryEncoder requires category_encoders: pip install category-encoders")
        elif self.encoding_method == 'hash':
            try:
                from category_encoders import HashingEncoder
                self.encoder = HashingEncoder(**self.encoding_params)
            except ImportError:
                self.encoder = None
        elif self.encoding_method == 'count':
            try:
                from category_encoders import CountEncoder
                self.encoder = CountEncoder(**self.encoding_params)
            except ImportError:
                self.encoder = None
        else:
            raise ValueError(f"Unsupported encoding method: {self.encoding_method}")
    
    def fit(self, X: Union[np.ndarray, List, pd.Series]) -> 'CategoricalPreprocessor':
        """拟合
        
        Args:
            X: 输入数据
            
        Returns:
            自身
        """
        X = np.array(X).reshape(-1, 1) if X.ndim == 1 else X
        
        self._init_encoder()
        
        if self.encoding_method == 'label':
            self.encoder.fit(X.ravel())
            self.categories_ = list(self.encoder.classes_)
        else:
            self.encoder.fit(X)
            if hasattr(self.encoder, 'categories_'):
                self.categories_ = self.encoder.categories_
        
        self.fitted = True
        return self
    
    def transform(self, X: Union[np.ndarray, List, pd.Series]) -> np.ndarray:
        """转换数据"""
        if not self.fitted:
            raise ValueError("Preprocessor not fitted yet. Call fit() first.")
        
        X = np.array(X).reshape(-1, 1) if X.ndim == 1 else X
        
        if self.encoding_method == 'label':
            # 处理未知值
            transformed = []
            for val in X.ravel():
                if val in self.encoder.classes_:
                    transformed.append(self.encoder.transform([val])[0])
                else:
                    if self.handle_unknown == 'ignore':
                        transformed.append(-1)
                    else:
                        raise ValueError(f"Unknown category: {val}")
            return np.array(transformed).reshape(-1, 1)
        else:
            return self.encoder.transform(X)
    
    def fit_transform(self, X: Union[np.ndarray, List, pd.Series]) -> np.ndarray:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X)
    
    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """逆转换"""
        if not self.fitted:
            raise ValueError("Preprocessor not fitted yet. Call fit() first.")
        
        if self.encoding_method == 'label':
            return self.encoder.inverse_transform(X.ravel())
        else:
            return self.encoder.inverse_transform(X)
    
    def get_feature_names(self) -> List[str]:
        """获取特征名称"""
        if not self.fitted:
            return []
        
        if self.encoding_method == 'onehot' and hasattr(self.encoder, 'get_feature_names_out'):
            return self.encoder.get_feature_names_out()
        elif self.encoding_method == 'ordinal':
            return [f"encoded_{i}" for i in range(X.shape[1])]
        elif self.encoding_method == 'label':
            return ['encoded']
        else:
            return [f"feature_{i}" for i in range(self.encoder.get_feature_names().shape[1])]


class FeatureEngineering:
    """特征工程类"""
    
    def __init__(self):
        self.polynomial = None
        self.interaction = None
    
    @staticmethod
    def create_polynomial_features(X: np.ndarray, degree: int = 2,
                                   interaction_only: bool = False,
                                   include_bias: bool = False) -> np.ndarray:
        """创建多项式特征
        
        Args:
            X: 输入特征
            degree: 多项式度数
            interaction_only: 是否仅交互项
            include_bias: 是否包含偏置项
            
        Returns:
            多项式特征
        """
        poly = PolynomialFeatures(degree=degree, interaction_only=interaction_only,
                                 include_bias=include_bias)
        return poly.fit_transform(X)
    
    @staticmethod
    def create_interaction_features(X: np.ndarray, max_features: int = None) -> np.ndarray:
        """创建交互特征
        
        Args:
            X: 输入特征
            max_features: 最大特征数
            
        Returns:
            交互特征
        """
        n_features = X.shape[1]
        interactions = []
        
        for i in range(n_features):
            for j in range(i + 1, n_features):
                interactions.append(X[:, i] * X[:, j])
        
        if interactions:
            result = np.column_stack(interactions)
            if max_features and result.shape[1] > max_features:
                # 随机选择特征
                indices = np.random.choice(result.shape[1], max_features, replace=False)
                result = result[:, indices]
            return result
        else:
            return np.array([]).reshape(len(X), 0)
    
    @staticmethod
    def create_ratio_features(X: np.ndarray, pairs: List[Tuple[int, int]] = None) -> np.ndarray:
        """创建比率特征
        
        Args:
            X: 输入特征
            pairs: 要创建比率的特征对列表 [(i, j), ...]
            
        Returns:
            比率特征
        """
        n_features = X.shape[1]
        
        if pairs is None:
            # 创建所有可能的比率
            pairs = [(i, j) for i in range(n_features) for j in range(n_features) if i != j]
        
        ratios = []
        for i, j in pairs:
            # 避免除零
            denominator = X[:, j].copy()
            denominator[denominator == 0] = 1e-10
            ratios.append(X[:, i] / denominator)
        
        return np.column_stack(ratios) if ratios else np.array([]).reshape(len(X), 0)
    
    @staticmethod
    def create_binned_features(X: np.ndarray, n_bins: int = 10,
                               strategy: str = 'uniform') -> np.ndarray:
        """创建分箱特征
        
        Args:
            X: 输入特征
            n_bins: 箱数
            strategy: 分箱策略 ('uniform', 'quantile')
            
        Returns:
            分箱特征
        """
        from sklearn.preprocessing import KBinsDiscretizer
        discretizer = KBinsDiscretizer(n_bins=n_bins, encode='onehot-dense', strategy=strategy)
        return discretizer.fit_transform(X)
    
    @staticmethod
    def create_aggregate_features(X: np.ndarray, groups: List[List[int]]) -> np.ndarray:
        """创建聚合特征
        
        Args:
            X: 输入特征
            groups: 特征组列表 [[0,1,2], [3,4], ...]
            
        Returns:
            聚合特征
        """
        aggregates = []
        
        for group in groups:
            group_data = X[:, group]
            aggregates.append(np.mean(group_data, axis=1))
            aggregates.append(np.std(group_data, axis=1))
            aggregates.append(np.max(group_data, axis=1))
            aggregates.append(np.min(group_data, axis=1))
        
        return np.column_stack(aggregates) if aggregates else np.array([]).reshape(len(X), 0)
    
    @staticmethod
    def create_window_features(X: np.ndarray, window_sizes: List[int],
                               functions: List[str] = None) -> np.ndarray:
        """创建窗口特征（用于时间序列）
        
        Args:
            X: 输入特征
            window_sizes: 窗口大小列表
            functions: 聚合函数列表
            
        Returns:
            窗口特征
        """
        if functions is None:
            functions = ['mean', 'std', 'max', 'min']
        
        windows = []
        
        for window in window_sizes:
            for i in range(len(X) - window + 1):
                window_data = X[i:i + window]
                window_features = []
                
                for func_name in functions:
                    if func_name == 'mean':
                        window_features.append(np.mean(window_data, axis=0))
                    elif func_name == 'std':
                        window_features.append(np.std(window_data, axis=0))
                    elif func_name == 'max':
                        window_features.append(np.max(window_data, axis=0))
                    elif func_name == 'min':
                        window_features.append(np.min(window_data, axis=0))
                    elif func_name == 'median':
                        window_features.append(np.median(window_data, axis=0))
                    elif func_name == 'skew':
                        from scipy.stats import skew
                        window_features.append(skew(window_data, axis=0))
                    elif func_name == 'kurtosis':
                        from scipy.stats import kurtosis
                        window_features.append(kurtosis(window_data, axis=0))
                
                windows.append(np.concatenate(window_features))
        
        return np.array(windows)


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self, outlier_method: str = 'iqr', outlier_threshold: float = 1.5,
                 missing_strategy: str = 'mean', missing_fill_value: Any = None,
                 duplicate_strategy: str = 'first', standardize_format: bool = True):
        """初始化数据清洗器
        
        Args:
            outlier_method: 异常值处理方法 ('iqr', 'zscore', 'isolation_forest', 'none')
            outlier_threshold: 异常值阈值
            missing_strategy: 缺失值处理策略 ('mean', 'median', 'mode', 'constant', 'drop', 'knn')
            missing_fill_value: 填充值
            duplicate_strategy: 重复值处理策略 ('first', 'last', 'drop')
            standardize_format: 是否标准化格式
        """
        self.outlier_method = outlier_method
        self.outlier_threshold = outlier_threshold
        self.missing_strategy = missing_strategy
        self.missing_fill_value = missing_fill_value
        self.duplicate_strategy = duplicate_strategy
        self.standardize_format = standardize_format
        
        self.outlier_mask = None
        self.imputer = None
    
    def detect_outliers(self, X: np.ndarray) -> np.ndarray:
        """检测异常值
        
        Args:
            X: 输入数据
            
        Returns:
            异常值掩码
        """
        X = np.array(X)
        
        if self.outlier_method == 'iqr':
            Q1 = np.percentile(X, 25, axis=0)
            Q3 = np.percentile(X, 75, axis=0)
            IQR = Q3 - Q1
            lower = Q1 - self.outlier_threshold * IQR
            upper = Q3 + self.outlier_threshold * IQR
            
            mask = np.any((X < lower) | (X > upper), axis=1)
            return mask
        
        elif self.outlier_method == 'zscore':
            from scipy import stats
            z_scores = np.abs(stats.zscore(X))
            mask = np.any(z_scores > self.outlier_threshold, axis=1)
            return mask
        
        elif self.outlier_method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest
            iso_forest = IsolationForest(contamination='auto', random_state=42)
            labels = iso_forest.fit_predict(X)
            return labels == -1
        
        else:
            return np.zeros(len(X), dtype=bool)
    
    def remove_outliers(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """移除异常值"""
        self.outlier_mask = self.detect_outliers(X)
        X_clean = X[~self.outlier_mask]
        
        if y is not None:
            y_clean = y[~self.outlier_mask]
            return X_clean, y_clean
        
        return X_clean, None
    
    def handle_missing_values(self, X: np.ndarray) -> np.ndarray:
        """处理缺失值"""
        X = np.array(X)
        
        if self.missing_strategy == 'drop':
            return X[~np.isnan(X).any(axis=1)]
        
        elif self.missing_strategy == 'knn':
            self.imputer = KNNImputer()
            return self.imputer.fit_transform(X)
        
        else:
            if self.missing_strategy == 'mean':
                self.imputer = SimpleImputer(strategy='mean')
            elif self.missing_strategy == 'median':
                self.imputer = SimpleImputer(strategy='median')
            elif self.missing_strategy == 'mode':
                self.imputer = SimpleImputer(strategy='most_frequent')
            elif self.missing_strategy == 'constant':
                self.imputer = SimpleImputer(strategy='constant', fill_value=self.missing_fill_value)
            else:
                raise ValueError(f"Unsupported missing strategy: {self.missing_strategy}")
            
            return self.imputer.fit_transform(X)
    
    def remove_duplicates(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """移除重复值"""
        # 找到唯一行的索引
        _, unique_indices = np.unique(X, axis=0, return_index=True)
        
        if self.duplicate_strategy == 'first':
            # 保留第一个出现的
            unique_indices = np.sort(unique_indices)
        elif self.duplicate_strategy == 'last':
            # 保留最后一个出现的
            unique_indices = np.sort(unique_indices)[::-1]
        elif self.duplicate_strategy == 'drop':
            # 移除所有重复的
            from collections import Counter
            X_tuple = [tuple(row) for row in X]
            counter = Counter(X_tuple)
            unique_indices = [i for i, row in enumerate(X_tuple) if counter[row] == 1]
            unique_indices = np.array(unique_indices)
        
        X_unique = X[unique_indices]
        
        if y is not None:
            y_unique = y[unique_indices]
            return X_unique, y_unique
        
        return X_unique, None
    
    def clean(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """完整清洗流程"""
        # 处理异常值
        X, y = self.remove_outliers(X, y)
        
        # 处理缺失值
        X = self.handle_missing_values(X)
        
        # 处理重复值
        X, y = self.remove_duplicates(X, y)
        
        return X, y


class DataNormalizer:
    """数据归一化器"""
    
    def __init__(self, method: str = 'standard', **kwargs):
        """初始化归一化器
        
        Args:
            method: 归一化方法
            **kwargs: 其他参数
        """
        self.method = method
        self.kwargs = kwargs
        self.normalizer = None
        self.fitted = False
    
    def fit(self, X: np.ndarray) -> 'DataNormalizer':
        """拟合"""
        if self.method == 'standard':
            self.normalizer = StandardScaler(**self.kwargs)
        elif self.method == 'minmax':
            self.normalizer = MinMaxScaler(**self.kwargs)
        elif self.method == 'robust':
            self.normalizer = RobustScaler(**self.kwargs)
        elif self.method == 'maxabs':
            from sklearn.preprocessing import MaxAbsScaler
            self.normalizer = MaxAbsScaler(**self.kwargs)
        elif self.method == 'l2':
            from sklearn.preprocessing import Normalizer
            self.normalizer = Normalizer(norm='l2', **self.kwargs)
        elif self.method == 'l1':
            from sklearn.preprocessing import Normalizer
            self.normalizer = Normalizer(norm='l1', **self.kwargs)
        elif self.method == 'power':
            self.normalizer = PowerTransformer(**self.kwargs)
        elif self.method == 'quantile':
            self.normalizer = QuantileTransformer(**self.kwargs)
        else:
            raise ValueError(f"Unsupported normalization method: {self.method}")
        
        self.normalizer.fit(X)
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """转换"""
        if not self.fitted:
            raise ValueError("Normalizer not fitted yet")
        return self.normalizer.transform(X)
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X)
    
    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """逆转换"""
        if not self.fitted:
            raise ValueError("Normalizer not fitted yet")
        return self.normalizer.inverse_transform(X)


class DataEncoder:
    """数据编码器"""
    
    def __init__(self, method: str = 'onehot', **kwargs):
        """初始化编码器
        
        Args:
            method: 编码方法
            **kwargs: 其他参数
        """
        self.method = method
        self.kwargs = kwargs
        self.encoder = None
        self.fitted = False
    
    def fit(self, X: np.ndarray) -> 'DataEncoder':
        """拟合"""
        if self.method == 'onehot':
            self.encoder = OneHotEncoder(sparse_output=False, **self.kwargs)
        elif self.method == 'label':
            self.encoder = LabelEncoder()
        elif self.method == 'ordinal':
            self.encoder = OrdinalEncoder(**self.kwargs)
        elif self.method == 'target':
            from sklearn.preprocessing import TargetEncoder
            self.encoder = TargetEncoder(**self.kwargs)
        else:
            raise ValueError(f"Unsupported encoding method: {self.method}")
        
        if self.method == 'label':
            self.encoder.fit(X.ravel())
        else:
            self.encoder.fit(X)
        
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """转换"""
        if not self.fitted:
            raise ValueError("Encoder not fitted yet")
        
        if self.method == 'label':
            return self.encoder.transform(X.ravel()).reshape(-1, 1)
        else:
            return self.encoder.transform(X)
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X)
    
    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """逆转换"""
        if not self.fitted:
            raise ValueError("Encoder not fitted yet")
        
        if self.method == 'label':
            return self.encoder.inverse_transform(X.ravel())
        else:
            return self.encoder.inverse_transform(X)


class FeatureSelector:
    """特征选择器"""
    
    def __init__(self, method: str = 'kbest', n_features: int = 10,
                 score_func: Optional[Callable] = None, **kwargs):
        """初始化特征选择器
        
        Args:
            method: 选择方法 ('kbest', 'percentile', 'rfe', 'rfecv', 'model_based')
            n_features: 选择特征数
            score_func: 评分函数
            **kwargs: 其他参数
        """
        self.method = method
        self.n_features = n_features
        self.score_func = score_func
        self.kwargs = kwargs
        self.selector = None
        self.fitted = False
    
    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'FeatureSelector':
        """拟合"""
        if self.method == 'kbest':
            if self.score_func is None:
                if y is not None and len(np.unique(y)) < 10:
                    self.score_func = f_classif
                else:
                    self.score_func = f_regression
            self.selector = SelectKBest(score_func=self.score_func, k=self.n_features, **self.kwargs)
        
        elif self.method == 'percentile':
            from sklearn.feature_selection import SelectPercentile
            if self.score_func is None:
                self.score_func = f_classif
            self.selector = SelectPercentile(score_func=self.score_func, percentile=self.n_features, **self.kwargs)
        
        elif self.method == 'rfe':
            from sklearn.feature_selection import RFE
            from sklearn.svm import SVC
            estimator = self.kwargs.get('estimator', SVC(kernel="linear"))
            self.selector = RFE(estimator, n_features_to_select=self.n_features, **self.kwargs)
        
        elif self.method == 'rfecv':
            from sklearn.feature_selection import RFECV
            from sklearn.svm import SVC
            estimator = self.kwargs.get('estimator', SVC(kernel="linear"))
            cv = self.kwargs.get('cv', 5)
            self.selector = RFECV(estimator, cv=cv, **self.kwargs)
        
        elif self.method == 'model_based':
            from sklearn.feature_selection import SelectFromModel
            estimator = self.kwargs.get('estimator')
            if estimator is None:
                raise ValueError("estimator is required for model_based selection")
            self.selector = SelectFromModel(estimator, **self.kwargs)
        
        else:
            raise ValueError(f"Unsupported selection method: {self.method}")
        
        self.selector.fit(X, y)
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """转换"""
        if not self.fitted:
            raise ValueError("Selector not fitted yet")
        return self.selector.transform(X)
    
    def fit_transform(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        """拟合并转换"""
        self.fit(X, y)
        return self.transform(X)
    
    def get_support(self, indices: bool = False) -> np.ndarray:
        """获取支持的特征"""
        if not self.fitted:
            raise ValueError("Selector not fitted yet")
        return self.selector.get_support(indices=indices)
    
    def get_feature_importances(self) -> np.ndarray:
        """获取特征重要性"""
        if not self.fitted:
            return np.array([])
        
        if hasattr(self.selector, 'scores_'):
            return self.selector.scores_
        elif hasattr(self.selector, 'feature_importances_'):
            return self.selector.feature_importances_
        elif hasattr(self.selector, 'coef_'):
            return np.abs(self.selector.coef_).flatten()
        else:
            return np.array([])


class DimensionalityReducer:
    """降维器"""
    
    def __init__(self, method: str = 'pca', n_components: int = 2, **kwargs):
        """初始化降维器
        
        Args:
            method: 降维方法 ('pca', 'svd', 'tsne', 'isomap', 'factor', 'ica', 'nmf')
            n_components: 目标维度
            **kwargs: 其他参数
        """
        self.method = method
        self.n_components = n_components
        self.kwargs = kwargs
        self.reducer = None
        self.fitted = False
    
    def fit(self, X: np.ndarray) -> 'DimensionalityReducer':
        """拟合"""
        if self.method == 'pca':
            self.reducer = PCA(n_components=self.n_components, **self.kwargs)
        elif self.method == 'svd':
            self.reducer = TruncatedSVD(n_components=self.n_components, **self.kwargs)
        elif self.method == 'tsne':
            self.reducer = TSNE(n_components=self.n_components, **self.kwargs)
        elif self.method == 'isomap':
            self.reducer = Isomap(n_components=self.n_components, **self.kwargs)
        elif self.method == 'factor':
            self.reducer = FactorAnalysis(n_components=self.n_components, **self.kwargs)
        elif self.method == 'ica':
            self.reducer = FastICA(n_components=self.n_components, **self.kwargs)
        elif self.method == 'nmf':
            self.reducer = NMF(n_components=self.n_components, **self.kwargs)
        else:
            raise ValueError(f"Unsupported dimensionality reduction method: {self.method}")
        
        self.reducer.fit(X)
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """转换"""
        if not self.fitted:
            raise ValueError("Reducer not fitted yet")
        
        if self.method == 'tsne':
            # t-SNE 不支持 transform
            return self.reducer.fit_transform(X)
        
        return self.reducer.transform(X)
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X)
    
    def get_explained_variance(self) -> np.ndarray:
        """获取解释方差（仅PCA）"""
        if not self.fitted or self.method != 'pca':
            return np.array([])
        return self.reducer.explained_variance_ratio_


class OutlierDetector:
    """异常值检测器"""
    
    def __init__(self, method: str = 'isolation_forest', contamination: float = 'auto', **kwargs):
        """初始化异常值检测器
        
        Args:
            method: 检测方法 ('isolation_forest', 'lof', 'one_class_svm', 'elliptic_envelope')
            contamination: 污染率
            **kwargs: 其他参数
        """
        self.method = method
        self.contamination = contamination
        self.kwargs = kwargs
        self.detector = None
        self.fitted = False
    
    def fit(self, X: np.ndarray) -> 'OutlierDetector':
        """拟合"""
        if self.method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest
            self.detector = IsolationForest(contamination=self.contamination, **self.kwargs)
        elif self.method == 'lof':
            from sklearn.neighbors import LocalOutlierFactor
            self.detector = LocalOutlierFactor(contamination=self.contamination, **self.kwargs)
        elif self.method == 'one_class_svm':
            from sklearn.svm import OneClassSVM
            self.detector = OneClassSVM(**self.kwargs)
        elif self.method == 'elliptic_envelope':
            from sklearn.covariance import EllipticEnvelope
            self.detector = EllipticEnvelope(contamination=self.contamination, **self.kwargs)
        else:
            raise ValueError(f"Unsupported outlier detection method: {self.method}")
        
        self.detector.fit(X)
        self.fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测异常值"""
        if not self.fitted:
            raise ValueError("Detector not fitted yet")
        
        if self.method == 'lof':
            # LOF 需要特殊处理
            return self.detector.fit_predict(X) == -1
        else:
            return self.detector.predict(X) == -1
    
    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """拟合并预测"""
        self.fit(X)
        return self.predict(X)
    
    def get_outlier_scores(self, X: np.ndarray) -> np.ndarray:
        """获取异常分数"""
        if not self.fitted:
            raise ValueError("Detector not fitted yet")
        
        if hasattr(self.detector, 'score_samples'):
            return self.detector.score_samples(X)
        elif hasattr(self.detector, 'decision_function'):
            return self.detector.decision_function(X)
        else:
            return np.array([])


class MissingValueHandler:
    """缺失值处理器"""
    
    def __init__(self, strategy: str = 'mean', fill_value: Any = None,
                 add_indicator: bool = False, **kwargs):
        """初始化缺失值处理器
        
        Args:
            strategy: 处理策略 ('mean', 'median', 'mode', 'constant', 'knn', 'interpolate')
            fill_value: 填充值
            add_indicator: 是否添加缺失指示器
            **kwargs: 其他参数
        """
        self.strategy = strategy
        self.fill_value = fill_value
        self.add_indicator = add_indicator
        self.kwargs = kwargs
        self.imputer = None
        self.indicator = None
        self.fitted = False
    
    def fit(self, X: np.ndarray) -> 'MissingValueHandler':
        """拟合"""
        X = np.array(X)
        
        if self.strategy in ['mean', 'median', 'mode', 'constant']:
            self.imputer = SimpleImputer(strategy=self.strategy, fill_value=self.fill_value, **self.kwargs)
        elif self.strategy == 'knn':
            self.imputer = KNNImputer(**self.kwargs)
        elif self.strategy == 'interpolate':
            from sklearn.experimental import enable_iterative_imputer
            from sklearn.impute import IterativeImputer
            self.imputer = IterativeImputer(**self.kwargs)
        else:
            raise ValueError(f"Unsupported missing value strategy: {self.strategy}")
        
        if self.add_indicator:
            from sklearn.impute import MissingIndicator
            self.indicator = MissingIndicator(**self.kwargs)
            self.indicator.fit(X)
        
        self.imputer.fit(X)
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """转换"""
        if not self.fitted:
            raise ValueError("Handler not fitted yet")
        
        X_imputed = self.imputer.transform(X)
        
        if self.add_indicator and self.indicator:
            X_missing = self.indicator.transform(X)
            X_imputed = np.hstack([X_imputed, X_missing])
        
        return X_imputed
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X)


class DataSplitter:
    """数据分割器"""
    
    def __init__(self, test_size: float = 0.2, val_size: float = 0.1,
                 stratify: bool = False, random_state: int = 42,
                 shuffle: bool = True):
        """初始化数据分割器
        
        Args:
            test_size: 测试集比例
            val_size: 验证集比例
            stratify: 是否分层抽样
            random_state: 随机种子
            shuffle: 是否打乱
        """
        self.test_size = test_size
        self.val_size = val_size
        self.stratify = stratify
        self.random_state = random_state
        self.shuffle = shuffle
    
    def split(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> Tuple:
        """分割数据
        
        Args:
            X: 特征
            y: 标签
            
        Returns:
            (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        from sklearn.model_selection import train_test_split
        
        # 先分割出测试集
        stratify_param = y if self.stratify else None
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state,
            stratify=stratify_param, shuffle=self.shuffle
        )
        
        # 再从剩余数据中分割出验证集
        if self.val_size > 0:
            val_ratio = self.val_size / (1 - self.test_size)
            stratify_param = y_temp if self.stratify else None
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp, y_temp, test_size=val_ratio, random_state=self.random_state,
                stratify=stratify_param, shuffle=self.shuffle
            )
        else:
            X_train, y_train = X_temp, y_temp
            X_val, y_val = np.array([]), np.array([])
        
        if y is None:
            return X_train, X_val, X_test
        else:
            return X_train, X_val, X_test, y_train, y_val, y_test


class DataBalancer:
    """数据平衡器"""
    
    def __init__(self, method: str = 'smote', random_state: int = 42, **kwargs):
        """初始化数据平衡器
        
        Args:
            method: 平衡方法 ('smote', 'adasyn', 'random_over', 'random_under', 'nearmiss')
            random_state: 随机种子
            **kwargs: 其他参数
        """
        self.method = method
        self.random_state = random_state
        self.kwargs = kwargs
        self.balancer = None
        self.fitted = False
    
    def fit_resample(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """拟合并重采样"""
        if self.method == 'smote':
            self.balancer = SMOTE(random_state=self.random_state, **self.kwargs)
        elif self.method == 'adasyn':
            self.balancer = ADASYN(random_state=self.random_state, **self.kwargs)
        elif self.method == 'random_over':
            self.balancer = RandomOverSampler(random_state=self.random_state, **self.kwargs)
        elif self.method == 'random_under':
            self.balancer = RandomUnderSampler(random_state=self.random_state, **self.kwargs)
        elif self.method == 'nearmiss':
            self.balancer = NearMiss(**self.kwargs)
        else:
            raise ValueError(f"Unsupported balancing method: {self.method}")
        
        X_resampled, y_resampled = self.balancer.fit_resample(X, y)
        self.fitted = True
        
        return X_resampled, y_resampled


class SequencePreprocessor:
    """序列预处理器（用于时间序列、文本序列等）"""
    
    def __init__(self, max_length: int = 100, padding: str = 'post',
                 truncating: str = 'post', value: float = 0.0):
        """初始化序列预处理器
        
        Args:
            max_length: 最大长度
            padding: 填充位置 ('pre', 'post')
            truncating: 截断位置 ('pre', 'post')
            value: 填充值
        """
        self.max_length = max_length
        self.padding = padding
        self.truncating = truncating
        self.value = value
    
    def pad_sequences(self, sequences: List[np.ndarray]) -> np.ndarray:
        """填充序列"""
        padded = []
        
        for seq in sequences:
            seq = np.array(seq)
            
            if len(seq) > self.max_length:
                if self.truncating == 'pre':
                    seq = seq[-self.max_length:]
                else:
                    seq = seq[:self.max_length]
            
            if len(seq) < self.max_length:
                pad_len = self.max_length - len(seq)
                if self.padding == 'pre':
                    pad = np.full(pad_len, self.value)
                    seq = np.concatenate([pad, seq])
                else:
                    pad = np.full(pad_len, self.value)
                    seq = np.concatenate([seq, pad])
            
            padded.append(seq)
        
        return np.array(padded)
    
    def create_sequences(self, data: np.ndarray, seq_length: int,
                        target_length: int = 1, step: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """创建序列样本
        
        Args:
            data: 输入数据
            seq_length: 序列长度
            target_length: 目标长度
            step: 步长
            
        Returns:
            (X, y)
        """
        X, y = [], []
        
        for i in range(0, len(data) - seq_length - target_length + 1, step):
            X.append(data[i:i + seq_length])
            y.append(data[i + seq_length:i + seq_length + target_length])
        
        return np.array(X), np.array(y)


class AudioPreprocessor:
    """音频预处理器"""
    
    def __init__(self, sample_rate: int = 16000, duration: float = None,
                 normalize: bool = True, augment: bool = False):
        """初始化音频预处理器
        
        Args:
            sample_rate: 采样率
            duration: 音频时长（秒）
            normalize: 是否归一化
            augment: 是否数据增强
        """
        self.sample_rate = sample_rate
        self.duration = duration
        self.normalize = normalize
        self.augment = augment
    
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """加载音频"""
        audio, sr = librosa.load(audio_path, sr=self.sample_rate)
        return audio, sr
    
    def resample(self, audio: np.ndarray, orig_sr: int) -> np.ndarray:
        """重采样"""
        if orig_sr != self.sample_rate:
            audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=self.sample_rate)
        return audio
    
    def pad_or_truncate(self, audio: np.ndarray) -> np.ndarray:
        """填充或截断到指定时长"""
        if self.duration is None:
            return audio
        
        target_length = int(self.duration * self.sample_rate)
        
        if len(audio) > target_length:
            audio = audio[:target_length]
        elif len(audio) < target_length:
            pad_length = target_length - len(audio)
            audio = np.pad(audio, (0, pad_length), 'constant')
        
        return audio
    
    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """归一化音频"""
        if self.normalize:
            audio = audio / (np.max(np.abs(audio)) + 1e-10)
        return audio
    
    def extract_mfcc(self, audio: np.ndarray, n_mfcc: int = 13) -> np.ndarray:
        """提取MFCC特征"""
        mfcc = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=n_mfcc)
        return mfcc.T
    
    def extract_mel_spectrogram(self, audio: np.ndarray, n_mels: int = 128) -> np.ndarray:
        """提取梅尔频谱图"""
        mel = librosa.feature.melspectrogram(y=audio, sr=self.sample_rate, n_mels=n_mels)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        return mel_db.T
    
    def extract_chroma(self, audio: np.ndarray) -> np.ndarray:
        """提取色度特征"""
        chroma = librosa.feature.chroma_stft(y=audio, sr=self.sample_rate)
        return chroma.T
    
    def preprocess(self, audio_path: str) -> np.ndarray:
        """预处理音频"""
        audio, sr = self.load_audio(audio_path)
        audio = self.resample(audio, sr)
        audio = self.pad_or_truncate(audio)
        audio = self.normalize_audio(audio)
        return audio


class TimeSeriesPreprocessor:
    """时间序列预处理器"""
    
    def __init__(self, normalize: bool = True, differencing: bool = False,
                 detrend: bool = False, seasonality: bool = False):
        """初始化时间序列预处理器
        
        Args:
            normalize: 是否归一化
            differencing: 是否差分
            detrend: 是否去趋势
            seasonality: 是否去除季节性
        """
        self.normalize = normalize
        self.differencing = differencing
        self.detrend = detrend
        self.seasonality = seasonality
        self.mean = None
        self.std = None
        self.trend = None
    
    def normalize_ts(self, ts: np.ndarray) -> np.ndarray:
        """归一化"""
        if self.normalize:
            self.mean = np.mean(ts)
            self.std = np.std(ts)
            ts = (ts - self.mean) / (self.std + 1e-10)
        return ts
    
    def denormalize(self, ts: np.ndarray) -> np.ndarray:
        """反归一化"""
        if self.normalize and self.mean is not None and self.std is not None:
            ts = ts * self.std + self.mean
        return ts
    
    def difference(self, ts: np.ndarray, order: int = 1) -> np.ndarray:
        """差分"""
        if self.differencing and order > 0:
            for _ in range(order):
                ts = np.diff(ts)
        return ts
    
    def inverse_difference(self, ts: np.ndarray, original: np.ndarray, order: int = 1) -> np.ndarray:
        """反差分"""
        if self.differencing and order > 0:
            # 简单实现，实际需要更复杂的处理
            ts = np.concatenate([[original[0]], ts])
        return ts
    
    def preprocess(self, ts: np.ndarray) -> np.ndarray:
        """预处理"""
        ts = self.normalize_ts(ts)
        ts = self.difference(ts)
        return ts


class PipelinePreprocessor:
    """流水线预处理器"""
    
    def __init__(self, steps: List[Tuple[str, Any]]):
        """初始化流水线预处理器
        
        Args:
            steps: 预处理步骤列表 [(名称, 处理器), ...]
        """
        self.steps = steps
        self.pipeline = Pipeline(steps)
        self.fitted = False
    
    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'PipelinePreprocessor':
        """拟合"""
        self.pipeline.fit(X, y)
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """转换"""
        if not self.fitted:
            raise ValueError("Pipeline not fitted yet")
        return self.pipeline.transform(X)
    
    def fit_transform(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        """拟合并转换"""
        return self.pipeline.fit_transform(X, y)
    
    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """逆转换"""
        if not self.fitted:
            raise ValueError("Pipeline not fitted yet")
        
        # 从后向前应用逆转换
        X_inv = X
        for name, step in reversed(self.steps):
            if hasattr(step, 'inverse_transform'):
                X_inv = step.inverse_transform(X_inv)
        
        return X_inv


def create_preprocessing_pipeline(data_type: str, **kwargs) -> PipelinePreprocessor:
    """创建预处理器流水线
    
    Args:
        data_type: 数据类型 ('numerical', 'categorical', 'text', 'image', 'mixed')
        **kwargs: 其他参数
        
    Returns:
        预处理器流水线
    """
    steps = []
    
    if data_type == 'numerical':
        steps = [
            ('cleaner', DataCleaner(**kwargs.get('cleaner', {}))),
            ('scaler', NumericalPreprocessor(**kwargs.get('scaler', {})))
        ]
    elif data_type == 'categorical':
        steps = [
            ('encoder', CategoricalPreprocessor(**kwargs.get('encoder', {})))
        ]
    elif data_type == 'text':
        steps = [
            ('text_preprocessor', TextPreprocessor(**kwargs.get('text', {})))
        ]
    elif data_type == 'image':
        steps = [
            ('image_preprocessor', ImagePreprocessor(**kwargs.get('image', {})))
        ]
    elif data_type == 'mixed':
        steps = [
            ('cleaner', DataCleaner(**kwargs.get('cleaner', {}))),
            ('scaler', NumericalPreprocessor(**kwargs.get('scaler', {}))),
            ('feature_engineering', FeatureEngineering())
        ]
    else:
        raise ValueError(f"Unsupported data type: {data_type}")
    
    return PipelinePreprocessor(steps)