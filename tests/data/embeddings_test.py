# pylint: disable=no-self-use,invalid-name
import gzip

import numpy
import pytest
from deep_qa.common.checks import ConfigurationError
from deep_qa.data.data_indexer import DataIndexer
from deep_qa.data.embeddings import PretrainedEmbeddings
from deep_qa.models.text_classification import ClassificationModel
from deep_qa.testing.test_case import DeepQaTestCase


class TestPretrainedEmbeddings(DeepQaTestCase):
    # pylint: disable=protected-access
    def test_get_embedding_layer_uses_correct_embedding_dim(self):
        data_indexer = DataIndexer()
        embeddings_filename = self.TEST_DIR + "embeddings.gz"
        with gzip.open(embeddings_filename, 'wb') as embeddings_file:
            embeddings_file.write("word1 1.0 2.3 -1.0\n".encode('utf-8'))
            embeddings_file.write("word2 0.1 0.4 -4.0\n".encode('utf-8'))
        embedding_layer = PretrainedEmbeddings.get_embedding_layer(embeddings_filename, data_indexer)
        assert embedding_layer.output_dim == 3

        with gzip.open(embeddings_filename, 'wb') as embeddings_file:
            embeddings_file.write("word1 1.0 2.3 -1.0 3.1\n".encode('utf-8'))
            embeddings_file.write("word2 0.1 0.4 -4.0 -1.2\n".encode('utf-8'))
        embedding_layer = PretrainedEmbeddings.get_embedding_layer(embeddings_filename, data_indexer)
        assert embedding_layer.output_dim == 4

    def test_get_embedding_layer_crashes_when_embedding_dim_is_one(self):
        data_indexer = DataIndexer()
        embeddings_filename = self.TEST_DIR + "embeddings.gz"
        with gzip.open(embeddings_filename, 'wb') as embeddings_file:
            embeddings_file.write("dimensionality 3\n".encode('utf-8'))
            embeddings_file.write("word1 1.0 2.3 -1.0\n".encode('utf-8'))
            embeddings_file.write("word2 0.1 0.4 -4.0\n".encode('utf-8'))
        with pytest.raises(Exception):
            PretrainedEmbeddings.get_embedding_layer(embeddings_filename, data_indexer)

    def test_get_embedding_layer_skips_inconsistent_lines(self):
        data_indexer = DataIndexer()
        data_indexer.add_word_to_index("word1")
        data_indexer.add_word_to_index("word2")
        embeddings_filename = self.TEST_DIR + "embeddings.gz"
        with gzip.open(embeddings_filename, 'wb') as embeddings_file:
            embeddings_file.write("word1 1.0 2.3 -1.0\n".encode('utf-8'))
            embeddings_file.write("word2 0.1 0.4 \n".encode('utf-8'))
        embedding_layer = PretrainedEmbeddings.get_embedding_layer(embeddings_filename, data_indexer)
        print(embedding_layer.weights)
        word_vector = embedding_layer._initial_weights[0][data_indexer.get_word_index("word2")]
        assert not numpy.allclose(word_vector[:2], numpy.asarray([0.1, 0.4]))

    def test_get_embedding_layer_actually_initializes_word_vectors_correctly(self):
        data_indexer = DataIndexer()
        data_indexer.add_word_to_index("word")
        embeddings_filename = self.TEST_DIR + "embeddings.gz"
        with gzip.open(embeddings_filename, 'wb') as embeddings_file:
            embeddings_file.write("word 1.0 2.3 -1.0\n".encode('utf-8'))
        embedding_layer = PretrainedEmbeddings.get_embedding_layer(embeddings_filename, data_indexer)
        word_vector = embedding_layer._initial_weights[0][data_indexer.get_word_index("word")]
        assert numpy.allclose(word_vector, numpy.asarray([1.0, 2.3, -1.0]))

    def test_get_embedding_layer_initializes_unseen_words_randomly_not_zero(self):
        data_indexer = DataIndexer()
        data_indexer.add_word_to_index("word2")
        embeddings_filename = self.TEST_DIR + "embeddings.gz"
        with gzip.open(embeddings_filename, 'wb') as embeddings_file:
            embeddings_file.write("word 1.0 2.3 -1.0\n".encode('utf-8'))
        embedding_layer = PretrainedEmbeddings.get_embedding_layer(embeddings_filename, data_indexer)
        word_vector = embedding_layer._initial_weights[0][data_indexer.get_word_index("word2")]
        assert not numpy.allclose(word_vector, numpy.asarray([0.0, 0.0, 0.0]))

    def test_embedding_will_not_project_random_embeddings(self):
        self.write_pretrained_vector_files()
        self.write_true_false_model_files()
        with pytest.raises(ConfigurationError):
            args = {
                    "embeddings": {
                            "words": {
                                    "dimension": 5,
                                    "project": True,
                                    "fine_tune": True,
                                    "dropout": 0.2
                            }
                    }
            }
            model = self.get_model(ClassificationModel, args)
            model.train()

    def test_projection_dim_not_equal_to_pretrained_dim_with_no_projection_flag_raises_error(self):
        self.write_pretrained_vector_files()
        self.write_true_false_model_files()
        with pytest.raises(ConfigurationError):
            args = {
                    "embeddings": {
                            "words": {
                                    "dimension": 13,
                                    "pretrained_file": self.PRETRAINED_VECTORS_GZIP,
                                    "project": False,
                                    "fine_tune": False,
                                    "dropout": 0.2
                            }
                    }
            }
            model = self.get_model(ClassificationModel, args)
            model.train()
