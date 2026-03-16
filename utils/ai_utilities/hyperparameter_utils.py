"""
超参数优化工具模块

提供AI模型超参数优化的工具函数，包括网格搜索、随机搜索、贝叶斯优化、遗传算法等。
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score
from sklearn.base import BaseEstimator
import itertools
import warnings
from collections import defaultdict
import time
import json


class ParameterSpaceBuilder:
    """参数空间构建器"""
    
    @staticmethod
    def build_grid_space(param_grid: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
        """构建网格搜索参数空间
        
        Args:
            param_grid: 参数网格字典
            
        Returns:
            格式化的参数空间
        """
        return param_grid
    
    @staticmethod
    def build_random_space(param_distributions: Dict[str, Any]) -> Dict[str, Any]:
        """构建随机搜索参数空间
        
        Args:
            param_distributions: 参数分布字典
            
        Returns:
            格式化的参数空间
        """
        return param_distributions
    
    @staticmethod
    def build_bayesian_space(param_definitions: Dict[str, Dict]) -> Dict[str, Dict]:
        """构建贝叶斯优化参数空间
        
        Args:
            param_definitions: 参数定义字典
            
        Returns:
            格式化的参数空间
        """
        space = {}
        for name, config in param_definitions.items():
            if config['type'] == 'integer':
                space[name] = ('integer', config['low'], config['high'])
            elif config['type'] == 'float':
                space[name] = ('float', config['low'], config['high'])
            elif config['type'] == 'categorical':
                space[name] = ('categorical', config['choices'])
            else:
                space[name] = ('categorical', config.get('choices', [config.get('default')]))
        
        return space
    
    @staticmethod
    def create_param_grid_from_ranges(param_ranges: Dict[str, Tuple]) -> Dict[str, List]:
        """从范围创建参数网格
        
        Args:
            param_ranges: 参数范围字典 {name: (start, end, step)}
            
        Returns:
            参数网格
        """
        param_grid = {}
        for name, (start, end, step) in param_ranges.items():
            if isinstance(step, int):
                param_grid[name] = list(range(start, end + 1, step))
            else:
                param_grid[name] = [start + i * step for i in range(int((end - start) / step) + 1)]
        
        return param_grid


class GridSearchOptimizer:
    """网格搜索优化器"""
    
    def __init__(self, model: BaseEstimator, param_grid: Dict[str, List[Any]],
                 cv: int = 5, scoring: str = 'accuracy', n_jobs: int = -1,
                 verbose: int = 0, random_state: int = 42):
        """初始化网格搜索优化器
        
        Args:
            model: 模型对象
            param_grid: 参数网格
            cv: 交叉验证折数
            scoring: 评分指标
            n_jobs: 并行作业数
            verbose: 详细程度
            random_state: 随机种子
        """
        self.model = model
        self.param_grid = param_grid
        self.cv = cv
        self.scoring = scoring
        self.n_jobs = n_jobs
        self.verbose = verbose
        self.random_state = random_state
        
        self.grid_search = None
        self.best_params_ = None
        self.best_score_ = None
        self.cv_results_ = None
    
    def optimize(self, X: np.ndarray, y: np.ndarray, 
                 fit_params: Optional[Dict] = None) -> Dict[str, Any]:
        """执行网格搜索优化
        
        Args:
            X: 特征矩阵
            y: 目标值
            fit_params: 拟合参数
            
        Returns:
            优化结果
        """
        self.grid_search = GridSearchCV(
            estimator=self.model,
            param_grid=self.param_grid,
            cv=self.cv,
            scoring=self.scoring,
            n_jobs=self.n_jobs,
            verbose=self.verbose,
            return_train_score=True
        )
        
        self.grid_search.fit(X, y, **(fit_params or {}))
        
        self.best_params_ = self.grid_search.best_params_
        self.best_score_ = self.grid_search.best_score_
        self.cv_results_ = self.grid_search.cv_results_
        
        return {
            'best_params': self.best_params_,
            'best_score': self.best_score_,
            'cv_results': self.cv_results_,
            'best_estimator': self.grid_search.best_estimator_
        }
    
    def get_param_combinations_count(self) -> int:
        """获取参数组合数量"""
        count = 1
        for values in self.param_grid.values():
            count *= len(values)
        return count
    
    def get_results_df(self) -> pd.DataFrame:
        """获取结果DataFrame"""
        if self.cv_results_ is None:
            return pd.DataFrame()
        
        return pd.DataFrame(self.cv_results_)


class RandomSearchOptimizer:
    """随机搜索优化器"""
    
    def __init__(self, model: BaseEstimator, param_distributions: Dict[str, Any],
                 n_iter: int = 100, cv: int = 5, scoring: str = 'accuracy',
                 n_jobs: int = -1, verbose: int = 0, random_state: int = 42):
        """初始化随机搜索优化器
        
        Args:
            model: 模型对象
            param_distributions: 参数分布
            n_iter: 迭代次数
            cv: 交叉验证折数
            scoring: 评分指标
            n_jobs: 并行作业数
            verbose: 详细程度
            random_state: 随机种子
        """
        self.model = model
        self.param_distributions = param_distributions
        self.n_iter = n_iter
        self.cv = cv
        self.scoring = scoring
        self.n_jobs = n_jobs
        self.verbose = verbose
        self.random_state = random_state
        
        self.random_search = None
        self.best_params_ = None
        self.best_score_ = None
        self.cv_results_ = None
    
    def optimize(self, X: np.ndarray, y: np.ndarray,
                 fit_params: Optional[Dict] = None) -> Dict[str, Any]:
        """执行随机搜索优化"""
        self.random_search = RandomizedSearchCV(
            estimator=self.model,
            param_distributions=self.param_distributions,
            n_iter=self.n_iter,
            cv=self.cv,
            scoring=self.scoring,
            n_jobs=self.n_jobs,
            verbose=self.verbose,
            random_state=self.random_state,
            return_train_score=True
        )
        
        self.random_search.fit(X, y, **(fit_params or {}))
        
        self.best_params_ = self.random_search.best_params_
        self.best_score_ = self.random_search.best_score_
        self.cv_results_ = self.random_search.cv_results_
        
        return {
            'best_params': self.best_params_,
            'best_score': self.best_score_,
            'cv_results': self.cv_results_,
            'best_estimator': self.random_search.best_estimator_
        }
    
    def get_results_df(self) -> pd.DataFrame:
        """获取结果DataFrame"""
        if self.cv_results_ is None:
            return pd.DataFrame()
        
        return pd.DataFrame(self.cv_results_)


class BayesianOptimizer:
    """贝叶斯优化器"""
    
    def __init__(self, model: BaseEstimator, param_space: Dict[str, Dict],
                 n_iter: int = 50, cv: int = 5, scoring: str = 'accuracy',
                 random_state: int = 42, verbose: int = 0):
        """初始化贝叶斯优化器
        
        Args:
            model: 模型对象
            param_space: 参数空间定义
            n_iter: 迭代次数
            cv: 交叉验证折数
            scoring: 评分指标
            random_state: 随机种子
            verbose: 详细程度
        """
        self.model = model
        self.param_space = param_space
        self.n_iter = n_iter
        self.cv = cv
        self.scoring = scoring
        self.random_state = random_state
        self.verbose = verbose
        
        self.optimizer = None
        self.best_params_ = None
        self.best_score_ = None
        self.trials_ = []
    
    def _objective(self, params: Dict) -> float:
        """目标函数"""
        # 设置模型参数
        self.model.set_params(**params)
        
        # 交叉验证评分
        scores = cross_val_score(self.model, self.X, self.y, cv=self.cv, scoring=self.scoring)
        return np.mean(scores)
    
    def optimize(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """执行贝叶斯优化"""
        self.X = X
        self.y = y
        
        try:
            import optuna
            
            def objective(trial):
                params = {}
                for name, config in self.param_space.items():
                    if config['type'] == 'integer':
                        params[name] = trial.suggest_int(name, config['low'], config['high'])
                    elif config['type'] == 'float':
                        params[name] = trial.suggest_float(name, config['low'], config['high'])
                    elif config['type'] == 'categorical':
                        params[name] = trial.suggest_categorical(name, config['choices'])
                    elif config['type'] == 'logfloat':
                        params[name] = trial.suggest_float(name, config['low'], config['high'], log=True)
                
                return self._objective(params)
            
            # 创建study
            study = optuna.create_study(
                direction='maximize',
                sampler=optuna.samplers.TPESampler(seed=self.random_state)
            )
            
            # 优化
            study.optimize(objective, n_trials=self.n_iter, show_progress_bar=self.verbose > 0)
            
            self.best_params_ = study.best_params
            self.best_score_ = study.best_value
            self.trials_ = study.trials
            self.study = study
            
        except ImportError:
            # 如果没有optuna，使用简单的随机搜索
            warnings.warn("Optuna not installed. Using random search instead.")
            return self._random_optimize()
        
        return {
            'best_params': self.best_params_,
            'best_score': self.best_score_,
            'trials': self.trials_,
            'study': self.study if hasattr(self, 'study') else None
        }
    
    def _random_optimize(self) -> Dict[str, Any]:
        """备用的随机优化"""
        best_score = -np.inf
        best_params = None
        trials = []
        
        for i in range(self.n_iter):
            # 随机采样参数
            params = {}
            for name, config in self.param_space.items():
                if config['type'] == 'integer':
                    params[name] = np.random.randint(config['low'], config['high'] + 1)
                elif config['type'] == 'float':
                    params[name] = np.random.uniform(config['low'], config['high'])
                elif config['type'] == 'categorical':
                    params[name] = np.random.choice(config['choices'])
            
            # 评估
            score = self._objective(params)
            trials.append({'params': params, 'score': score})
            
            if score > best_score:
                best_score = score
                best_params = params
            
            if self.verbose:
                print(f"Iteration {i+1}/{self.n_iter}: Score = {score:.4f}")
        
        self.best_params_ = best_params
        self.best_score_ = best_score
        self.trials_ = trials
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'trials': trials
        }
    
    def plot_optimization_history(self, save_path: str = None):
        """绘制优化历史"""
        if hasattr(self, 'study') and self.study:
            import plotly
            fig = optuna.visualization.plot_optimization_history(self.study)
            if save_path:
                plotly.io.write_html(fig, save_path)
            else:
                fig.show()
    
    def plot_param_importance(self, save_path: str = None):
        """绘制参数重要性"""
        if hasattr(self, 'study') and self.study:
            import plotly
            fig = optuna.visualization.plot_param_importances(self.study)
            if save_path:
                plotly.io.write_html(fig, save_path)
            else:
                fig.show()


class GeneticOptimizer:
    """遗传算法优化器"""
    
    def __init__(self, model: BaseEstimator, param_space: Dict[str, Dict],
                 population_size: int = 50, generations: int = 20,
                 mutation_rate: float = 0.1, crossover_rate: float = 0.8,
                 cv: int = 5, scoring: str = 'accuracy', random_state: int = 42,
                 verbose: int = 0):
        """初始化遗传算法优化器
        
        Args:
            model: 模型对象
            param_space: 参数空间
            population_size: 种群大小
            generations: 迭代代数
            mutation_rate: 变异率
            crossover_rate: 交叉率
            cv: 交叉验证折数
            scoring: 评分指标
            random_state: 随机种子
            verbose: 详细程度
        """
        self.model = model
        self.param_space = param_space
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.cv = cv
        self.scoring = scoring
        self.random_state = random_state
        self.verbose = verbose
        
        np.random.seed(random_state)
        
        self.best_params_ = None
        self.best_score_ = None
        self.history_ = []
    
    def _create_individual(self) -> Dict[str, Any]:
        """创建个体"""
        individual = {}
        for name, config in self.param_space.items():
            if config['type'] == 'integer':
                individual[name] = np.random.randint(config['low'], config['high'] + 1)
            elif config['type'] == 'float':
                individual[name] = np.random.uniform(config['low'], config['high'])
            elif config['type'] == 'categorical':
                individual[name] = np.random.choice(config['choices'])
        return individual
    
    def _create_population(self) -> List[Dict[str, Any]]:
        """创建种群"""
        return [self._create_individual() for _ in range(self.population_size)]
    
    def _fitness(self, individual: Dict[str, Any]) -> float:
        """计算适应度"""
        self.model.set_params(**individual)
        scores = cross_val_score(self.model, self.X, self.y, cv=self.cv, scoring=self.scoring)
        return np.mean(scores)
    
    def _evaluate_population(self, population: List[Dict]) -> List[float]:
        """评估种群"""
        return [self._fitness(ind) for ind in population]
    
    def _select_parents(self, population: List[Dict], fitness: List[float]) -> List[Dict]:
        """选择父代（锦标赛选择）"""
        parents = []
        tournament_size = 3
        
        for _ in range(len(population)):
            # 随机选择参赛者
            indices = np.random.choice(len(population), tournament_size, replace=False)
            tournament_fitness = [fitness[i] for i in indices]
            winner_idx = indices[np.argmax(tournament_fitness)]
            parents.append(population[winner_idx].copy())
        
        return parents
    
    def _crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        """交叉操作"""
        if np.random.random() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        
        child1, child2 = {}, {}
        
        for name in parent1.keys():
            if np.random.random() < 0.5:
                child1[name] = parent1[name]
                child2[name] = parent2[name]
            else:
                child1[name] = parent2[name]
                child2[name] = parent1[name]
        
        return child1, child2
    
    def _mutate(self, individual: Dict) -> Dict:
        """变异操作"""
        mutated = individual.copy()
        
        for name, config in self.param_space.items():
            if np.random.random() < self.mutation_rate:
                if config['type'] == 'integer':
                    step = max(1, int((config['high'] - config['low']) * 0.1))
                    value = mutated[name] + np.random.randint(-step, step + 1)
                    mutated[name] = np.clip(value, config['low'], config['high'])
                elif config['type'] == 'float':
                    sigma = (config['high'] - config['low']) * 0.1
                    value = mutated[name] + np.random.normal(0, sigma)
                    mutated[name] = np.clip(value, config['low'], config['high'])
                elif config['type'] == 'categorical':
                    mutated[name] = np.random.choice(config['choices'])
        
        return mutated
    
    def optimize(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """执行遗传算法优化"""
        self.X = X
        self.y = y
        
        # 初始化种群
        population = self._create_population()
        
        for generation in range(self.generations):
            # 评估种群
            fitness = self._evaluate_population(population)
            
            # 记录最佳个体
            best_idx = np.argmax(fitness)
            best_score = fitness[best_idx]
            best_individual = population[best_idx]
            
            self.history_.append({
                'generation': generation,
                'best_score': best_score,
                'mean_score': np.mean(fitness),
                'std_score': np.std(fitness)
            })
            
            if self.verbose:
                print(f"Generation {generation+1}/{self.generations}: "
                      f"Best = {best_score:.4f}, Mean = {np.mean(fitness):.4f}")
            
            # 选择父代
            parents = self._select_parents(population, fitness)
            
            # 创建下一代
            next_population = []
            for i in range(0, len(parents), 2):
                if i + 1 < len(parents):
                    child1, child2 = self._crossover(parents[i], parents[i + 1])
                    next_population.append(self._mutate(child1))
                    next_population.append(self._mutate(child2))
                else:
                    next_population.append(self._mutate(parents[i]))
            
            # 精英保留
            next_population[0] = best_individual
            
            population = next_population
        
        # 最终评估
        fitness = self._evaluate_population(population)
        best_idx = np.argmax(fitness)
        self.best_params_ = population[best_idx]
        self.best_score_ = fitness[best_idx]
        
        return {
            'best_params': self.best_params_,
            'best_score': self.best_score_,
            'history': self.history_
        }
    
    def plot_history(self, save_path: str = None):
        """绘制优化历史"""
        import matplotlib.pyplot as plt
        
        generations = [h['generation'] for h in self.history_]
        best_scores = [h['best_score'] for h in self.history_]
        mean_scores = [h['mean_score'] for h in self.history_]
        
        plt.figure(figsize=(10, 6))
        plt.plot(generations, best_scores, 'b-', label='Best Score', linewidth=2)
        plt.plot(generations, mean_scores, 'r--', label='Mean Score', linewidth=2)
        plt.fill_between(generations,
                         [h['mean_score'] - h['std_score'] for h in self.history_],
                         [h['mean_score'] + h['std_score'] for h in self.history_],
                         alpha=0.2, color='red')
        
        plt.xlabel('Generation', fontsize=12)
        plt.ylabel('Score', fontsize=12)
        plt.title('Genetic Algorithm Optimization History', fontsize=14, fontweight='bold')
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()


class HyperbandOptimizer:
    """Hyperband优化器"""
    
    def __init__(self, model: BaseEstimator, param_space: Dict[str, Dict],
                 max_iter: int = 81, eta: int = 3, cv: int = 5,
                 scoring: str = 'accuracy', random_state: int = 42,
                 verbose: int = 0):
        """初始化Hyperband优化器
        
        Args:
            model: 模型对象
            param_space: 参数空间
            max_iter: 最大迭代次数
            eta: 缩减因子
            cv: 交叉验证折数
            scoring: 评分指标
            random_state: 随机种子
            verbose: 详细程度
        """
        self.model = model
        self.param_space = param_space
        self.max_iter = max_iter
        self.eta = eta
        self.cv = cv
        self.scoring = scoring
        self.random_state = random_state
        self.verbose = verbose
        
        np.random.seed(random_state)
        
        self.best_params_ = None
        self.best_score_ = None
        self.results_ = []
    
    def _sample_params(self) -> Dict[str, Any]:
        """采样参数"""
        params = {}
        for name, config in self.param_space.items():
            if config['type'] == 'integer':
                params[name] = np.random.randint(config['low'], config['high'] + 1)
            elif config['type'] == 'float':
                params[name] = np.random.uniform(config['low'], config['high'])
            elif config['type'] == 'categorical':
                params[name] = np.random.choice(config['choices'])
        return params
    
    def _evaluate(self, params: Dict[str, Any], n_iter: int) -> float:
        """评估参数配置"""
        # 这里简化处理，实际上应该使用部分数据或更少的迭代次数
        self.model.set_params(**params)
        scores = cross_val_score(self.model, self.X, self.y, cv=self.cv, scoring=self.scoring)
        return np.mean(scores)
    
    def optimize(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """执行Hyperband优化"""
        self.X = X
        self.y = y
        
        s_max = int(np.log(self.max_iter) / np.log(self.eta))
        B = (s_max + 1) * self.max_iter
        
        best_score = -np.inf
        best_params = None
        
        for s in reversed(range(s_max + 1)):
            n = int(np.ceil((B / self.max_iter) * (self.eta ** s) / (s + 1)))
            r = int(self.max_iter * (self.eta ** (-s)))
            
            if self.verbose:
                print(f"Hyperband iteration s={s}, n={n}, r={r}")
            
            # 初始化
            T = [self._sample_params() for _ in range(n)]
            
            for i in range(s + 1):
                # 运行和评估
                n_i = n * (self.eta ** (-i))
                r_i = int(r * (self.eta ** i))
                
                results = []
                for params in T:
                    score = self._evaluate(params, r_i)
                    results.append((params, score))
                    
                    if score > best_score:
                        best_score = score
                        best_params = params
                
                self.results_.extend([(r_i, params, score) for params, score in results])
                
                # 选择前 1/eta 的配置
                if i < s:
                    results.sort(key=lambda x: x[1], reverse=True)
                    n_keep = int(len(T) / self.eta)
                    T = [params for params, _ in results[:n_keep]]
        
        self.best_params_ = best_params
        self.best_score_ = best_score
        
        return {
            'best_params': self.best_params_,
            'best_score': self.best_score_,
            'results': self.results_
        }


class HyperparameterOptimizer:
    """超参数优化器（综合）"""
    
    def __init__(self, model: BaseEstimator, param_space: Dict[str, Dict],
                 method: str = 'grid', **kwargs):
        """初始化超参数优化器
        
        Args:
            model: 模型对象
            param_space: 参数空间
            method: 优化方法 ('grid', 'random', 'bayesian', 'genetic', 'hyperband')
            **kwargs: 其他参数
        """
        self.model = model
        self.param_space = param_space
        self.method = method
        self.kwargs = kwargs
        self.optimizer = None
        self.results_ = None
    
    def optimize(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """执行优化"""
        if self.method == 'grid':
            # 转换为网格格式
            param_grid = {}
            for name, config in self.param_space.items():
                if config['type'] == 'categorical':
                    param_grid[name] = config['choices']
                elif 'grid' in config:
                    param_grid[name] = config['grid']
                else:
                    # 为数值参数创建网格
                    if config['type'] == 'integer':
                        step = config.get('step', 1)
                        param_grid[name] = list(range(config['low'], config['high'] + 1, step))
                    elif config['type'] == 'float':
                        num = config.get('num', 10)
                        param_grid[name] = np.linspace(config['low'], config['high'], num).tolist()
            
            optimizer = GridSearchOptimizer(self.model, param_grid, **self.kwargs)
        
        elif self.method == 'random':
            # 转换为随机分布格式
            param_dist = {}
            for name, config in self.param_space.items():
                if config['type'] == 'categorical':
                    param_dist[name] = config['choices']
                elif config['type'] == 'integer':
                    from scipy.stats import randint
                    param_dist[name] = randint(config['low'], config['high'] + 1)
                elif config['type'] == 'float':
                    from scipy.stats import uniform
                    param_dist[name] = uniform(config['low'], config['high'] - config['low'])
            
            optimizer = RandomSearchOptimizer(self.model, param_dist, **self.kwargs)
        
        elif self.method == 'bayesian':
            optimizer = BayesianOptimizer(self.model, self.param_space, **self.kwargs)
        
        elif self.method == 'genetic':
            optimizer = GeneticOptimizer(self.model, self.param_space, **self.kwargs)
        
        elif self.method == 'hyperband':
            optimizer = HyperbandOptimizer(self.model, self.param_space, **self.kwargs)
        
        else:
            raise ValueError(f"Unsupported optimization method: {self.method}")
        
        self.optimizer = optimizer
        self.results_ = optimizer.optimize(X, y)
        
        return self.results_
    
    def get_best_params(self) -> Dict[str, Any]:
        """获取最佳参数"""
        if self.results_ is None:
            return {}
        return self.results_.get('best_params', {})
    
    def get_best_score(self) -> float:
        """获取最佳分数"""
        if self.results_ is None:
            return 0.0
        return self.results_.get('best_score', 0.0)
    
    def plot_results(self, save_path: str = None):
        """绘制优化结果"""
        if hasattr(self.optimizer, 'plot_history'):
            self.optimizer.plot_history(save_path)
        elif hasattr(self.optimizer, 'plot_optimization_history'):
            self.optimizer.plot_optimization_history(save_path)


class OptimizationAnalyzer:
    """优化结果分析器"""
    
    def __init__(self, results: Dict[str, Any]):
        """初始化分析器
        
        Args:
            results: 优化结果
        """
        self.results = results
        self.cv_results = results.get('cv_results', {})
    
    def get_parameter_importance(self) -> Dict[str, float]:
        """计算参数重要性"""
        if 'study' in self.results and hasattr(self.results['study'], 'trials'):
            try:
                import optuna
                study = self.results['study']
                importances = optuna.importance.get_param_importances(study)
                return dict(importances)
            except:
                pass
        
        # 使用简单的相关性分析
        if 'cv_results' in self.results:
            df = pd.DataFrame(self.cv_results)
            param_cols = [col for col in df.columns if col.startswith('param_')]
            score_col = 'mean_test_score'
            
            if param_cols and score_col in df.columns:
                importances = {}
                for col in param_cols:
                    # 尝试转换为数值
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        corr = df[[col, score_col]].corr().iloc[0, 1]
                        if not np.isnan(corr):
                            importances[col.replace('param_', '')] = abs(corr)
                    except:
                        pass
                
                return importances
        
        return {}
    
    def get_best_trials(self, n: int = 5) -> List[Dict]:
        """获取最佳试验"""
        if 'trials' in self.results:
            trials = self.results['trials']
            sorted_trials = sorted(trials, key=lambda x: x['value'] if hasattr(x, 'value') else x.get('score', 0), reverse=True)
            return sorted_trials[:n]
        
        if 'cv_results' in self.results:
            df = pd.DataFrame(self.cv_results)
            df_sorted = df.sort_values('mean_test_score', ascending=False)
            best_rows = df_sorted.head(n)
            
            trials = []
            for _, row in best_rows.iterrows():
                trial = {
                    'params': {k.replace('param_', ''): v for k, v in row.items() if k.startswith('param_')},
                    'score': row['mean_test_score'],
                    'std': row['std_test_score'] if 'std_test_score' in row else None
                }
                trials.append(trial)
            
            return trials
        
        return []
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """获取优化摘要"""
        summary = {
            'best_score': self.results.get('best_score'),
            'best_params': self.results.get('best_params'),
            'optimization_method': None,
            'n_iterations': 0,
            'total_time': None
        }
        
        if 'trials' in self.results:
            summary['n_iterations'] = len(self.results['trials'])
        
        if 'cv_results' in self.results:
            df = pd.DataFrame(self.cv_results)
            summary['n_iterations'] = len(df)
        
        if 'history' in self.results:
            summary['n_iterations'] = len(self.results['history'])
        
        return summary
    
    def generate_report(self) -> str:
        """生成分析报告"""
        report = "\n" + "=" * 60 + "\n"
        report += "HYPERPARAMETER OPTIMIZATION REPORT\n"
        report += "=" * 60 + "\n\n"
        
        summary = self.get_optimization_summary()
        report += f"Best Score: {summary['best_score']:.4f}\n"
        report += f"Best Parameters: {summary['best_params']}\n"
        report += f"Number of Iterations: {summary['n_iterations']}\n\n"
        
        # 参数重要性
        importances = self.get_parameter_importance()
        if importances:
            report += "Parameter Importance:\n"
            report += "-" * 40 + "\n"
            for param, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
                report += f"  {param}: {imp:.4f}\n"
            report += "\n"
        
        # 最佳试验
        best_trials = self.get_best_trials(5)
        if best_trials:
            report += "Top 5 Trials:\n"
            report += "-" * 40 + "\n"
            for i, trial in enumerate(best_trials, 1):
                report += f"  Trial {i}:\n"
                report += f"    Score: {trial['score']:.4f}\n"
                if 'std' in trial and trial['std']:
                    report += f"    Std: {trial['std']:.4f}\n"
                report += f"    Params: {trial['params']}\n"
        
        return report


def create_common_param_spaces(model_type: str) -> Dict[str, Dict]:
    """创建常见模型的参数空间
    
    Args:
        model_type: 模型类型
        
    Returns:
        参数空间字典
    """
    param_spaces = {
        'random_forest': {
            'n_estimators': {'type': 'integer', 'low': 50, 'high': 500, 'grid': [50, 100, 200, 300, 400, 500]},
            'max_depth': {'type': 'integer', 'low': 3, 'high': 20, 'grid': [3, 5, 10, 15, 20, None]},
            'min_samples_split': {'type': 'integer', 'low': 2, 'high': 20, 'grid': [2, 5, 10, 15, 20]},
            'min_samples_leaf': {'type': 'integer', 'low': 1, 'high': 10, 'grid': [1, 2, 4, 6, 8, 10]},
            'max_features': {'type': 'categorical', 'choices': ['sqrt', 'log2', None]}
        },
        'xgboost': {
            'n_estimators': {'type': 'integer', 'low': 50, 'high': 500, 'grid': [50, 100, 200, 300, 400, 500]},
            'max_depth': {'type': 'integer', 'low': 3, 'high': 10, 'grid': [3, 4, 5, 6, 7, 8, 9, 10]},
            'learning_rate': {'type': 'float', 'low': 0.01, 'high': 0.3, 'grid': [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]},
            'subsample': {'type': 'float', 'low': 0.6, 'high': 1.0, 'grid': [0.6, 0.7, 0.8, 0.9, 1.0]},
            'colsample_bytree': {'type': 'float', 'low': 0.6, 'high': 1.0, 'grid': [0.6, 0.7, 0.8, 0.9, 1.0]},
            'gamma': {'type': 'float', 'low': 0, 'high': 5, 'grid': [0, 0.1, 0.2, 0.5, 1, 2, 3, 4, 5]},
            'reg_alpha': {'type': 'float', 'low': 0, 'high': 10, 'grid': [0, 0.01, 0.1, 0.5, 1, 2, 5, 10]},
            'reg_lambda': {'type': 'float', 'low': 1, 'high': 10, 'grid': [1, 2, 3, 5, 7, 10]}
        },
        'lightgbm': {
            'n_estimators': {'type': 'integer', 'low': 50, 'high': 500, 'grid': [50, 100, 200, 300, 400, 500]},
            'max_depth': {'type': 'integer', 'low': 3, 'high': 15, 'grid': [3, 5, 7, 9, 11, 13, 15]},
            'learning_rate': {'type': 'float', 'low': 0.01, 'high': 0.3, 'grid': [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]},
            'num_leaves': {'type': 'integer', 'low': 10, 'high': 100, 'grid': [10, 20, 31, 40, 50, 60, 70, 80, 90, 100]},
            'min_child_samples': {'type': 'integer', 'low': 10, 'high': 50, 'grid': [10, 15, 20, 25, 30, 35, 40, 45, 50]},
            'subsample': {'type': 'float', 'low': 0.6, 'high': 1.0, 'grid': [0.6, 0.7, 0.8, 0.9, 1.0]},
            'colsample_bytree': {'type': 'float', 'low': 0.6, 'high': 1.0, 'grid': [0.6, 0.7, 0.8, 0.9, 1.0]},
            'reg_alpha': {'type': 'float', 'low': 0, 'high': 10, 'grid': [0, 0.01, 0.1, 0.5, 1, 2, 5, 10]},
            'reg_lambda': {'type': 'float', 'low': 0, 'high': 10, 'grid': [0, 0.01, 0.1, 0.5, 1, 2, 5, 10]}
        },
        'svm': {
            'C': {'type': 'float', 'low': 0.1, 'high': 1000, 'log': True, 'grid': [0.1, 1, 10, 100, 1000]},
            'kernel': {'type': 'categorical', 'choices': ['linear', 'rbf', 'poly', 'sigmoid']},
            'gamma': {'type': 'categorical', 'choices': ['scale', 'auto', 0.001, 0.01, 0.1, 1]},
            'degree': {'type': 'integer', 'low': 2, 'high': 5, 'grid': [2, 3, 4, 5]},
            'coef0': {'type': 'float', 'low': 0, 'high': 10, 'grid': [0, 0.1, 0.5, 1, 2, 5, 10]}
        },
        'neural_network': {
            'hidden_layer_sizes': {'type': 'categorical', 'choices': [(50,), (100,), (50, 50), (100, 50), (100, 100)]},
            'activation': {'type': 'categorical', 'choices': ['relu', 'tanh', 'logistic']},
            'alpha': {'type': 'float', 'low': 0.0001, 'high': 0.1, 'log': True, 'grid': [0.0001, 0.001, 0.01, 0.1]},
            'learning_rate': {'type': 'categorical', 'choices': ['constant', 'invscaling', 'adaptive']},
            'learning_rate_init': {'type': 'float', 'low': 0.001, 'high': 0.1, 'grid': [0.001, 0.01, 0.05, 0.1]},
            'batch_size': {'type': 'categorical', 'choices': [32, 64, 128, 256]},
            'max_iter': {'type': 'integer', 'low': 100, 'high': 1000, 'grid': [100, 200, 500, 1000]}
        }
    }
    
    return param_spaces.get(model_type, {})