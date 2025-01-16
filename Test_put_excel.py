import unittest
from unittest.mock import patch, MagicMock
from unittest.mock import Mock
import pandas as pd
import os
import sys
import config
import shutil
import warnings
from xml.etree.ElementTree import Element, tostring
warnings.filterwarnings("ignore")

# Mock sys.argv before importing put_excel
sys.argv = ["put_excel.py", "test_user", "test_pass", "test_input.xlsx", "test_output/"]
import put_excel as put_excel # Ensure the path is correct


class TestPutExcel(unittest.TestCase):

    def setUp(self):
        # Suppress warnings for the test case
        #warnings.simplefilter("ignore")
        # Temporary paths and data setup
        self.username = "test_user"
        self.password = "test_pass"
        self.excel_path = "test_input.xlsx"
        self.output_path = "test_output_temp/"
        self.excel_path_2 = "test_input_case2.xlsx"
        if not os.path.exists("test_output"):
            os.mkdir("test_output")


        # Mock input DataFrame for Excel processing
        data = {
            "TestCaseID": [1, 1, 2],
            "Doors ASIL": ["A", "B", "C"],
            "Doors Category": ["Security", "Not Security Relevant", "General"],
            "Previous ASIL Value RQM": ["QM", "-", "B"],
            "Previous Category Value RQM": ["Not Security Relevant", "Security Relevant", "General"],
            "TestCase State": ["approved", "not approved", "approved"],
        }
        self.test_df = pd.DataFrame(data)

        data_ccase2 = {
            "TestCaseID": [1, 1, 1],
            "Doors ASIL": ["-", "-", "-"],
            "Doors Category": ["General", "Not Security Relevant", "General"],
            "Previous ASIL Value RQM": ["QM", "-", "B"],
            "Previous Category Value RQM": ["Not Security Relevant", "Security Relevant", "General"],
            "TestCase State": ["approved", "not approved", "approved"],
        }
        self.test_df_case2 = pd.DataFrame(data_ccase2)

        # Write mock data to Excel
        os.makedirs(self.output_path, exist_ok=True)
        self.test_df.to_excel(self.excel_path, index=False)
        self.test_df_case2.to_excel(self.excel_path_2,index=False)

    @patch('requests.Session')
    @patch('requests.packages.urllib3.disable_warnings')
    def test_session_authentication_success(self, mock_disable_warnings, MockSession):
        # Mock successful session
        mock_session = MockSession.return_value
        mock_session.get.return_value.headers = {}
        mock_session.post.return_value.headers = {}

        session = put_excel.session_authentication(self.username, self.password)
        self.assertEqual(session, mock_session)

    def test_update_excel_wrt_rules_col(self):
        # Process Excel and validate updates
        updated_df = put_excel.update_excel_wrt_rules(self.excel_path)

        # Check new columns exist
        self.assertIn("Updated_ASIL_Values_RQM", updated_df.columns)
        self.assertIn("Updated_Security_Category_RQM", updated_df.columns)
    
    def test_update_excel_wrt_rules_senario_1(self):
        # Process Excel and validate updates
        updated_df = put_excel.update_excel_wrt_rules(self.excel_path)
        # Check new columns exist
        self.assertIn("Updated_ASIL_Values_RQM", updated_df.columns)
        self.assertIn("Updated_Security_Category_RQM", updated_df.columns)

        # Validate ASIL updates
        self.assertEqual(updated_df["Updated_ASIL_Values_RQM"][0], "B")
        self.assertEqual(updated_df["Updated_ASIL_Values_RQM"][2], "C")

        # Validate Security updates
        self.assertEqual(updated_df["Updated_Security_Category_RQM"][0], "Security Relevant")
        self.assertEqual(updated_df["Updated_Security_Category_RQM"][2], "Not Security Relevant")
    
    def test_update_excel_wrt_rules_senario_2(self):
        # Process Excel and validate updates
        updated_df = put_excel.update_excel_wrt_rules(self.excel_path_2)
        # Check new columns exist
        self.assertIn("Updated_ASIL_Values_RQM", updated_df.columns)
        self.assertIn("Updated_Security_Category_RQM", updated_df.columns)

        # Validate ASIL updates
        self.assertEqual(updated_df["Updated_ASIL_Values_RQM"][0], "-")

        # Validate Security updates
        self.assertEqual(updated_df["Updated_Security_Category_RQM"][0], "Not Security Relevant")

    @patch('put_excel.ElementTree')  # Mock the ElementTree module
    @patch('put_excel.config')  # Mock the config object
    def test_put_asil_category(self, mock_config, mock_etree):
        # Set up the mock config
        mock_config.UUID_dict = {'QM': 'uuid_QM', 'A': 'uuid_A'}
        mock_config.Security_Relevance = 'security_uuid'
        mock_config.new_state = 'new_state_value'
        mock_config.term = 'http://example.com/term/'

        # Set up a mock XML tree
        root = Element('root')
        tree_mock = Mock()
        tree_mock.getroot.return_value = root
        mock_etree.parse.return_value = tree_mock
        mock_etree.Element.return_value = root

        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content.decode.return_value = "<root></root>"
        mock_session.get.return_value = mock_response

        # Prepare the DataFrame
        data = {
            "TestCaseID": ["TC1"],
            "TestCaseURL": ["http://example.com/testcase/TC1"],
            "Previous ASIL Value RQM": ["QM"],
            "Updated_ASIL_Values_RQM": ["A"],
            "Previous Category Value RQM": ["Category1"],
            "Updated_Security_Category_RQM": ["Category2"],
            "TestCase State": ["approved"]
        }
        df = pd.DataFrame(data)

        # Call the function
        put_excel.put_ASIL_Category(mock_session, df)

        # Assertions
        mock_session.get.assert_called_once_with(
            "http://example.com/testcase/TC1", 
            headers={"OSLC-Core-Version": "2.0", "Accept": "application/xml"}
        )
        mock_session.put.assert_called_once()

    @patch('put_excel.XMLtoDict')  # Mocking the XMLtoDict class
    def test_convert_xml_dict_success(self, mock_XMLtoDict):
        # Mock XML input
        mock_resp = "<root><child>value</child></root>"
        
        # Mock parser behavior
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = {'root': {'child': 'value'}}
        mock_XMLtoDict.return_value = mock_parser_instance
        
        # Call the function
        from put_excel import convert_xml_dict
        result = convert_xml_dict(mock_resp)

        # Assertions
        self.assertEqual(result, {'root': {'child': 'value'}})
        mock_XMLtoDict.assert_called_once()  # Ensure XMLtoDict was instantiated
        mock_parser_instance.parse.assert_called_once_with(mock_resp)  # Ensure parse was called with the correct input

    @patch('put_excel.convert_xml_dict')
    @patch('put_excel.logger')
    @patch('put_excel.config')
    def test_fetch_ASIL_Security_both_values_present(self, mock_config, mock_logger, mock_convert):
        # Mock config for UUID_dict and security_vals
        mock_config.UUID_dict = {'ASIL_A': '123', 'ASIL_B': '456'}
        mock_config.security_vals = {'High': '789', 'Low': '012'}

        # Mock convert_xml_dict response with ASIL and Security values
        mock_convert.return_value = {
            '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF': {
                '{http://open-services.net/ns/qm#}TestCase': {
                    '{http://jazz.net/ns/qm/rqm#}category_723hYsvQEeWQV8qCNxbd3g': {
                        '@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource': 'http://example.com/ASIL_A:123.'
                    },
                    '{http://jazz.net/ns/qm/rqm#}category__9K0EV8pEe25Tv9E4OgVfQ': {
                        '@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource': 'http://example.com/High:789.'
                    }
                }
            }
        }

        from put_excel import fetch_ASIL_Security
        result = fetch_ASIL_Security('mock_response')

        self.assertEqual(result, ('ASIL_A', 'High'))  # Expect correct mapping of ASIL and Security
        mock_logger.info.assert_not_called()  # No log messages should be generated

    
    @patch('put_excel.convert_xml_dict')
    @patch('put_excel.logger')
    @patch('put_excel.config')
    def test_fetch_ASIL_Security_missing_ASIL(self, mock_config, mock_logger, mock_convert):
        # Mock config for UUID_dict and security_vals
        mock_config.UUID_dict = {'ASIL_A': '123', 'ASIL_B': '456'}
        mock_config.security_vals = {'High': '789', 'Low': '012'}

        # Mock convert_xml_dict response with only Security value
        mock_convert.return_value = {
            '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF': {
                '{http://open-services.net/ns/qm#}TestCase': {
                    '{http://jazz.net/ns/qm/rqm#}category__9K0EV8pEe25Tv9E4OgVfQ': {
                        '@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource': 'http://example.com/High:789.'
                    }
                }
            }
        }

        from put_excel import fetch_ASIL_Security
        result = fetch_ASIL_Security('mock_response')

        self.assertEqual(result, ('', 'High'))  # Expect empty ASIL and correct Security mapping
        mock_logger.info.assert_called_with("ASIL Value not present")  # Verify ASIL missing log


    @patch('put_excel.convert_xml_dict')
    @patch('put_excel.logger')
    @patch('put_excel.config')
    def test_fetch_ASIL_Security_missing_Security(self, mock_config, mock_logger, mock_convert):
        # Mock config for UUID_dict and security_vals
        mock_config.UUID_dict = {'ASIL_A': '123', 'ASIL_B': '456'}
        mock_config.security_vals = {'High': '789', 'Low': '012'}

        # Mock convert_xml_dict response with only ASIL value
        mock_convert.return_value = {
            '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF': {
                '{http://open-services.net/ns/qm#}TestCase': {
                    '{http://jazz.net/ns/qm/rqm#}category_723hYsvQEeWQV8qCNxbd3g': {
                        '@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource': 'http://example.com/ASIL_A:123.'
                    }
                }
            }
        }

        from put_excel import fetch_ASIL_Security
        result = fetch_ASIL_Security('mock_response')

        self.assertEqual(result, ('ASIL_A', 'Not Security Relevant'))  # Expect ASIL mapped and default Security
        mock_logger.info.assert_called_with("Security Value not present")  # Verify Security missing log

    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.excel_path):
            os.remove(self.excel_path)
        if os.path.exists(self.excel_path_2):
            os.remove(self.excel_path_2)
        if os.path.exists(self.output_path):
            os.rmdir(self.output_path)
        if os.path.exists("test_output"):
            shutil.rmtree("test_output")

if __name__ == "__main__":
    # Explicitly run the tests to prevent argument conflicts
    unittest.TextTestRunner().run(unittest.TestLoader().loadTestsFromTestCase(TestPutExcel))
