from __future__ import division

import numpy as np
import pandas as pd

from sklearn.preprocessing import balance_weights
from sklearn.cross_validation import ShuffleSplit
from sklearn import cross_validation

from bamboo.helpers import NUMERIC_TYPES


class ModelingData():
    """
    A class that stores a set of features and
    targets to be used for modeling.
    Provides functionality to do simple operations
    and manipulations of that data, removing
    boilerplate for ML code.
    """

    def __init__(self, features, targets, weights=None):
        self.features = features
        self.targets = targets
        self.weights = weights


    @staticmethod
    def from_dataframe(df, target, features=None):

        target_data = df[target]

        if features is None:
            features = [feature for feature in df.columns
                        if features != target]

        feature_data = df[features]

        return ModelingData(feature_data, target_data)


    def __len__(self):
        assert(len(self.features)==len(self.targets))
        return len(self.targets)


    def __str__(self):
        return "ModelingData({})".format(self.features.shape)


    def shape(self):
        return self.features.shape


    def num_classes(self):
        return len(self.targets.value_counts())


    def get_grouped_targets(self):
        return self.targets.groupby(self.targets)


    def is_orthogonal(self, other):
        indices = set(self.features.index)
        return not any(idx in indices for idx in other.features.index)


    def fit(self, clf, *args, **kwargs):
        return clf.fit(self.features, self.targets, *args, **kwargs)


    def train_test_split(self, *args, **kwargs):
        """
        Based on: sklearn.cross_validation.train_test_split
        Returns two ModelingData instances, the first representing
        training data and the scond representing testing data
        """
        test_size = kwargs.pop('test_size', None)
        train_size = kwargs.pop('train_size', None)
        random_state = kwargs.pop('random_state', None)

        if test_size is None and train_size is None:
                    test_size = 0.25

        n_samples = len(self.targets)

        cv = ShuffleSplit(n_samples, test_size=test_size,
                          train_size=train_size,
                          random_state=random_state)

        train, test = next(iter(cv))

        X_train = self.features.ix[train]
        y_train = self.targets.ix[train]

        X_test = self.features.ix[test]
        y_test = self.features.ix[test]

        return ModelingData(X_train, y_train), ModelingData(X_test, y_test)


    def _balance_by_truncation(self):
        """
        Take a modeling_data instance and return
        a new instance with the state variable
        balanced
        """

        group_size = self.targets.value_counts().min()
        grouped = self.features.groupby(self.targets)
        indices = []

        for name, group in grouped:
            indices.extend(group[:group_size].index)

        return ModelingData(self.features.ix[indices], self.targets.ix[indices])


    def _balance_by_sample_with_replace(self, size=None, exact=False):
        if size is None:
            size = len(self)

        approx_num_per_class = size / self.num_classes()

        indices = []

        for target, group in self.get_grouped_targets():
            indices.extend(np.random.choice(group.index.values, approx_num_per_class, replace=True))

        return ModelingData(self.features.ix[indices], self.targets.ix[indices])


    def get_balance_weights(self):
        return balance_weights(self.targets)


    def get_balanced(self, how='sample'):
        """
        Return a ModelingData derived from this instance
        but with balanced data (balanced according to
        the supplied options)
        """

        if how == 'truncate':
            return self._balance_by_truncation()
        elif how == 'sample':
            return self._balance_by_sample_with_replace()
        else:
            raise AttributeError()


    def hist(self, var_name, **kwargs):
        grouped = self.features[var_name].groupby(self.targets)
        return bamboo.plotting._series_hist(grouped, **kwargs)


    def stack(self, var_name, **kwargs):
        grouped = self.features[var_name].groupby(self.targets)
        return bamboo.plotting._draw_stacked_plot(grouped, **kwargs)


    def numeric_features(self):
        """
        Return a copy of thos ModelData that only contains
        numeric features
        """

        dtypes = self.features.dtypes
        numeric_dtypes = dtypes[dtypes.map(lambda x: x in NUMERIC_TYPES)]
        numeric_feature_names = list(numeric_dtypes.index.values)

        return ModelingData(self.features[numeric_feature_names], self.targets)


    def plot_auc_surve(self, clf):
        return plotting.plot_auc_curve(clf, self.features, self.targets)


    def predict_proba(self, clf):

        # The order of the targets in the classification predict_proba
        # matrix is based on the natural ordering of the input targets
        # So, we have to follow that natural ordering here
        ordered_targets = sorted(set(self.targets.values))

        scores = []

        for idx, row in self.features.iterrows():
            probabilities = clf.predict_proba(row)[0]

            res = {'index': idx}

            for target, proba in zip(ordered_targets, probabilities):
                res['proba_{}'.format(target)] = proba

            res['target'] = self.targets[idx]

            scores.append(res)

        return scores


    def predict(self, reg):

        scores = []

        for idx, row in self.features.iterrows():
            res = {'index': idx}
            res['predict'] = reg.predict(row)
            res['target'] = self.targets[idx]
            scores.append(res)

        return scores



    def _cross_validate_score(self, clf, fit=False, **kwargs):
        return cross_validation.cross_val-score(clf, self.features, self.targets, **kwargs)


    @staticmethod
    def get_threshold_summary(probability_summary, target, threshold=0.5, **kwargs):
        """
        Takes a probability summary, a target we're
        trying to predict (that is represented in the
        probability summary) and the threshold for
        that probability and returns a summary

        probabolity_summary = [{'proba_A': x, 'target': A}, {'proba_A': y, 'target': B}]
        """

        probability_label = "proba_{}".format(target)

        probability_summary = pd.DataFrame(probability_summary)

        positives = probability_summary[probability_summary[probability_label] >= threshold]
        true_positives = positives[positives['target']==target]
        false_positives = positives[positives['target']!=target]

        negatives = probability_summary[probability_summary[probability_label] < threshold]
        true_negatives = positives[positives['target'] != target]
        false_negatives = positives[positives['target'] == target]

        num = len(probability_summary)

        num_positives = len(positives)
        num_negatives = len(negatives)

        num_true_positives = len(true_positives)
        num_false_positives = len(false_positives)
        num_true_negatives = len(true_negatives)
        num_false_negatives = len(false_negatives)

        false_positive_rate = num_true_positives / num
        true_positive_rate = num_false_positives / num

        precision = num_true_positives / num_positives
        recall = num_true_positives / (num_true_positives + num_false_negatives)

        sensitivity = recall
        specificity = num_true_negatives / (num_false_positives + num_true_negatives) if num_false_positives + num_true_negatives > 0 else 1.0

        accuracy = (num_true_positives + num_true_negatives) / num
        f1 = 2*num_true_positives / (2*num_true_positives + num_false_positives + num_false_negatives)

        return {'threshold': threshold,
                'target': target,
                'true_positives': num_true_positives,
                'false_positives': num_false_positives,
                'true_negatives': num_true_negatives,
                'false_negatives': num_false_negatives,
                'precision': precision,
                'recall': recall,
                'sensiticity': sensitivity,
                'specificity': specificity,
                'accuracy': accuracy,
                'f1': f1,
                'false_positive_rate': false_positive_rate,
                'true_positive_rate': true_positive_rate}


        # for x in np.arange(0.0, 1.0, 0.01):
        #     thresholds.append(x)
        #     reduced = score_summary[score_summary.score >= x]
        #     approval = len(reduced) / len(score_summary)
        #     if len(reduced) == 0:
        #         repayment = 0.0
        #     else:
        #         repayment = reduced.target.sum() / len(reduced)
        #         approvals.append(approval)
        #         repayments.append(repayment)

        # return pd.DataFrame({'threshold': thresholds,
        #                      'approval': approvals,
        #                      'repayment': repayments})

