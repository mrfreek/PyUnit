import unittest
from unittest.mock import patch, MagicMock, Mock
from xml.etree.ElementTree import Element, tostring
import requests
import os
import warnings
import config
import pandas as pd
import get_excel as get_excel
warnings.simplefilter("ignore")
from get_excel import (
    session_authentication,
    keys_from_dict,
    convert_xml_dict,
    req_links_fetch,
    get_ctp_for_mtp
)
class TestMainFunctions(unittest.TestCase):

    def setUp(self):
        #warnings.simplefilter("ignore")
        self.session = Mock()
        self.username = "test_user"
        self.password = "test_pass"
        warnings.simplefilter("ignore")
        self.url = "http://example.com/api"
        self.flatten_list = [
            "http://example.com/testcase/1",
            "http://example.com/testcase/2"
        ]
        self.projectId = "ChildProject123"
        self.mtp_id = "MasterPlan456"

    @patch('requests.Session')
    @patch('requests.packages.urllib3.disable_warnings')
    def test_session_authentication_success(self, mock_disable_warnings, MockSession):
        # Mock successful session
        mock_session = MockSession.return_value
        mock_session.get.return_value.headers = {}
        mock_session.post.return_value.headers = {}

        session = get_excel.session_authentication(self.username, self.password)
        self.assertEqual(session, mock_session)

    @patch("get_excel.logger", create=True)
    def test_keys_from_dict(self, mock_logger):
        input_dict = [{'key1': 'value1'}, {'key2': 'value2'}]
        expected_output = ['value1', 'value2']
        self.assertEqual(keys_from_dict(input_dict), expected_output)

        input_dict = {'key': 'value'}
        expected_output = ['value']
        self.assertEqual(keys_from_dict(input_dict), expected_output)

    @patch("get_excel.logger", create=True)
    def test_keys_from_dict_caseempty(self, mock_logger):
        input_dict = {}
        expected_output = []
        self.assertEqual(keys_from_dict(input_dict), expected_output)
        input_dict = {'': ''}
        expected_output = ['']
        self.assertEqual(keys_from_dict(input_dict), expected_output)

    @patch('requests.Session.get')
    def test_convert_xml_dict_success(self, mock_get):
        mock_get.return_value.content = b"<root><key>value</key></root>"
        session = MagicMock()
        session.get = mock_get

        result = convert_xml_dict('http://fakeurl.com', session)
        self.assertIn('root', result)
        mock_get.assert_called_once_with('http://fakeurl.com')

    @patch('requests.Session.get')
    def test_convert_xml_dict_failure(self, mock_get):
        mock_get.side_effect = requests.RequestException("Network error")
        session = MagicMock()
        session.get = mock_get

        with self.assertRaises(Exception):
            convert_xml_dict('http://fakeurl.com', session)

    @patch("get_excel.logger", create=True)
    @patch('get_excel.convert_xml_dict')
    def test_get_ctp_for_mtp(self, mock_logger, mock_convert):
        mock_convert.return_value = {
            '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF': {
                '{http://open-services.net/ns/qm#}TestPlanQuery': {
                    '{http://open-services.net/ns/qm#}testPlan': {
                        '{http://open-services.net/ns/qm#}TestPlan': {
                            '{http://jazz.net/ns/qm/rqm#}hasChildPlan': [
                                {'@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource': 'testPlan1'},
                                {'@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource': 'testPlan2'}
                            ]
                        }
                    }
                }
            }
        }

        session = MagicMock()
        result = get_ctp_for_mtp('fake_mtp_id', session, '/fake/path')

        self.assertIsInstance(result, pd.DataFrame)

    @patch("get_excel.logger", create=True)        
    @patch('get_excel.convert_xml_dict')
    def test_get_ctp_for_mtp_no_child_test_plans(self, mock_convert, mock_logger):
        # Mocked return value for convert_xml_dict with no child test plans
        mock_convert.return_value = {
            '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF': {
                '{http://open-services.net/ns/qm#}TestPlanQuery': {
                    '{http://open-services.net/ns/qm#}testPlan': {
                        '{http://open-services.net/ns/qm#}TestPlan': {
                            # No 'hasChildPlan' key here
                        }
                    }
                }
            }
        }

        session = MagicMock()

        # Call the function with test inputs
        result = get_ctp_for_mtp('fake_mtp_id', session, '/fake/path')

        # Assertions
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        mock_convert.assert_called_once()

    def test_getMtpIDS_success(self):
        # Mock XML response with shortIdentifier tags
        root = Element("root")
        identifier1 = Element("{http://jazz.net/ns/qm/rqm#}shortIdentifier")
        identifier1.text = "ID1"
        root.append(identifier1)
        identifier2 = Element("{http://jazz.net/ns/qm/rqm#}shortIdentifier")
        identifier2.text = "ID2"
        root.append(identifier2)
        xml_content = tostring(root, encoding="utf8", method="xml").decode("utf8")

        # Mock the session.get response
        self.session.get.return_value.content = xml_content.encode("utf8")

        result = get_excel.getMtpIDS(self.url, self.session)

        # Assert the result
        self.assertEqual(result, ["ID1", "ID2"])

    @patch("get_excel.logger", create=True)
    def test_getMtpIDS_exception(self, mock_logger):

        # Mock the session.get to raise an exception
        self.session.get.side_effect = Exception("Error")

        # Call the function
        result = get_excel.getMtpIDS(self.url, self.session)

        # Assert the result
        self.assertEqual(result, [])
    
    @patch("get_excel.logger", create=True)
    @patch('get_excel.keys_from_dict')  # Mock keys_from_dict
    def test_child_test_plan_id_success(self,mock_logger,mock_keys_from_dict):#, mock_keys_from_dict):
        """TestCase - ChildTestPlanID: Successfully extracts ChildTestPlans for a valid input"""
        # Mock input data
        get_excel.mtp_id = "mock_mtp_id"
        input_value = {
            '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF': {
                '{http://open-services.net/ns/qm#}TestPlanQuery': {
                    '{http://open-services.net/ns/qm#}testPlan': {
                        '{http://open-services.net/ns/qm#}TestPlan': {
                            '{http://jazz.net/ns/qm/rqm#}hasChildPlan': [
                                {'child1': 'ChildPlan1'},
                                {'child2': 'ChildPlan2'}
                            ]
                        }
                    }
                }
            }
        }
        
        def mock_keys_function(input_dict):
            keys = []
            try:
                for i in input_dict:
                    keys.append(list(i.values()))
            except:
                dict_value_list = []
                dict_value_list.append(input_dict)
                for i in dict_value_list:
                    keys.append(list(i.values()))

            flatten_list = [element for sublist in keys for element in sublist]
            return flatten_list

        # Apply the mocked behavior
        mock_keys_from_dict.side_effect = mock_keys_function

        # Call the function under test
        result = get_excel.ChildTestPlanID(input_value)
        print("---------------------000000")
        print(result)
        ChildTestPlanID_ = keys_from_dict(result)
        # Assert the result matches the expected value
        self.assertEqual(ChildTestPlanID_, ["ChildPlan1", "ChildPlan2"])

if __name__ == '__main__':
    unittest.main()
