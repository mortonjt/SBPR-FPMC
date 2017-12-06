import unittest
import numpy as np
import numpy.testing as npt
from numpy.random import poisson, randint, random
from scipy.sparse import csr_matrix
from sbpr import (bootstrap, update_user_matrix, update_item_matrix,
                  score, simulate, split_dataset, user_item_ranks)
import copy


# will use the instacart dataset
# https://www.kaggle.com/c/instacart-market-basket-analysis
class TestSBPR(unittest.TestCase):

    def setUp(self):
        np.random.seed(0)
        # generate a quasi-realistic generative model
        # this will involve randomly generating the transition tensor
        kU = 10
        kI = 11
        kL = 11
        trans_probs, B = simulate(kU=kU, kI=kI,
                                  mu=0, scale=1,
                                  lamR=15, lamI=5)
        self.B = B
        self.trans_probs = trans_probs
        self.kU = kU   # number of users
        self.kL = kL   # number of items
        self.kI = kI   # number of items

    def test_simulation(self):
        np.random.seed(0)
        trans_probs, B = simulate(kU=3, kI=3,
                                  mu=0, scale=1,
                                  lamR=2, lamI=2)
        self.assertListEqual(B,
                             [[[2], [0], [1, 1, 1], [1, 0, 1, 0]],
                              [[2], [1, 0, 1, 0], [0]],
                              [[], [0, 0, 0]]])
        exp = np.array([[[0.58423523, 0.14936733, 0.26639744],
                         [0.57854881, 0.39829292, 0.02315827],
                         [0.59482294, 0.19771333, 0.20746373]],
                        [[0.21712474, 0.16632057, 0.61655469],
                         [0.44329537, 0.2338953 , 0.32280932],
                         [0.20943928, 0.66836778, 0.12219294]],
                        [[0.73090254, 0.22749237, 0.04160509],
                         [0.40284797, 0.4973912 , 0.09976083],
                         [0.88315015, 0.02131423, 0.09553562]]])
        npt.assert_allclose(trans_probs, exp, rtol=1e-4, atol=1e-4)

    def test_bootstrap(self):
        np.random.seed(0)
        I = list(range(11))
        res = bootstrap(self.B, I, 3)
        exp = np.array([[5, 0, 0, 3],
                        [7, 9, 5, 8],
                        [8, 1, 0, 5]])
        npt.assert_allclose(exp, res)

    def test_update_user_matrix_overwrite(self):
        np.random.seed(0)
        u, t, i, j = 5, 0, 0, 3
        rUI = 3  # rank of UI factor
        rIL = 3  # rank of IL factor

        V_ui = np.random.normal(size=(self.kU, rUI))
        V_iu = np.random.normal(size=(self.kI, rUI))
        V_li = np.random.normal(size=(self.kI, rIL))
        V_il = np.random.normal(size=(self.kI, rIL))

        exp_ui = copy.deepcopy(V_ui)
        exp_iu = copy.deepcopy(V_iu)

        update_user_matrix(u, t, i, j, self.B,
                           V_ui, V_iu,
                           V_li, V_il,
                           alpha=0.1, lam_ui=0, lam_iu=0)

        self.assertFalse(np.allclose(V_ui, exp_ui))
        self.assertFalse(np.allclose(V_iu, exp_iu))

    def test_update_item_matrix_overwrite(self):
        np.random.seed(0)
        u, t, i, j = 5, 0, 0, 3
        rUI = 3  # rank of UI factor
        rIL = 3  # rank of IL factor

        V_ui = np.random.normal(size=(self.kU, rUI))
        V_iu = np.random.normal(size=(self.kI, rUI))
        V_li = np.random.normal(size=(self.kI, rIL))
        V_il = np.random.normal(size=(self.kI, rIL))

        exp_li = copy.deepcopy(V_li)
        exp_il = copy.deepcopy(V_il)

        update_item_matrix(u, t, i, j, self.B,
                           V_ui, V_iu, V_li, V_il,
                           alpha=0.1, lam_il=0, lam_li=0)

        self.assertFalse(np.allclose(V_li, exp_li))
        self.assertFalse(np.allclose(V_il, exp_il))

    def test_all(self):
        np.random.seed(0)
        rUI = 3  # rank of UI factor
        rIL = 3  # rank of IL factor

        V_ui = np.random.normal(size=(self.kU, rUI))
        V_iu = np.random.normal(size=(self.kI, rUI))
        V_li = np.random.normal(size=(self.kI, rIL))
        V_il = np.random.normal(size=(self.kI, rIL))

        I = list(range(11))

        train, test = split_dataset(self.B)
        uranks = user_item_ranks(train, V_ui, V_iu, V_il, V_li)
        prev_auc_score = score(uranks, test, I, method='auc')
        print(test)
        for _ in range(10):
            boots = bootstrap(train, I, 10)
            for (u, t, i, j) in boots:
                update_user_matrix(u, t, i, j, train,
                                   V_ui, V_iu,
                                   V_li, V_il,
                                   alpha=0.1, lam_ui=0, lam_iu=0)

                update_item_matrix(u, t, i, j, train,
                                   V_ui, V_iu, V_li, V_il,
                                   alpha=0.1, lam_il=0, lam_li=0)

        # Run the metrics provided in the paper namely
        # i.e. half-life-utility
        #      precision and recall
        #      AUC under the ROC curve
        print(test)
        uranks = user_item_ranks(test, V_ui, V_iu, V_il, V_li)
        post_auc_score = score(uranks, test, I, method='auc')
        self.assertGreater(post_auc_score, prev_auc_score)


if __name__=="__main__":
    unittest.main()
