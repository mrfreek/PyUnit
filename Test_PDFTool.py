import os
import shutil
import unittest
from PyPDF4 import PdfFileWriter
import PDF_mod as PDF_mod
from unittest.mock import patch, mock_open, MagicMock
from io import BytesIO
from PDF_mod import get_display_name, remove_all_files, add_header, put_watermark
class TestPDFWatermarking(unittest.TestCase):

    def setUp(self):
        # Create temporary directories
        self.input_folder = "temp_input"
        self.output_folder = "temp_output"
        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

        # Create a mock input PDF
        self.input_pdf_path = os.path.join(self.input_folder, "sample.pdf")
        with open(self.input_pdf_path, "wb") as f:
            writer = PdfFileWriter()
            writer.addBlankPage(width=200, height=200)
            writer.write(f)

        # Create a mock watermark PDF
        self.watermark_pdf_path = "watermark.pdf"
        with open(self.watermark_pdf_path, "wb") as f:
            writer = PdfFileWriter()
            writer.addBlankPage(width=100, height=100)
            writer.write(f)

    def tearDown(self):
        # Clean up temporary directories and files
        shutil.rmtree(self.input_folder)
        shutil.rmtree(self.output_folder)
        if os.path.exists(self.watermark_pdf_path):
            os.remove(self.watermark_pdf_path)

    def test_put_watermark_success(self):
        result = PDF_mod.put_watermark(self.input_folder, self.output_folder, self.watermark_pdf_path)

        # Assert the function completes successfully
        self.assertEqual(result, 1)

        # Assert the output folder contains the watermarked file
        output_file_path = os.path.join(self.output_folder, "sample.pdf")
        self.assertTrue(os.path.exists(output_file_path))
    
    @patch("builtins.open", new_callable=mock_open, read_data="John Doe")
    def test_get_display_name(self, mock_file):
        # Test if get_display_name reads the user details correctly
        result = get_display_name()
        self.assertEqual(result, "John Doe")
        mock_file.assert_called_once_with('Userdetails.py', 'r')
    
    @patch("os.remove")
    @patch("glob.glob", return_value=["file1.txt", "file2.txt"])
    def test_remove_all_files(self, mock_glob, mock_remove):
        # Test if remove_all_files calls os.remove for each file
        test_path = "test_folder"
        remove_all_files(test_path)
        mock_glob.assert_called_once_with(test_path + "//*")
        self.assertEqual(mock_remove.call_count, 2)

    @patch("os.path.exists", return_value=False)
    @patch("os.listdir", return_value=["sample.pdf"])
    def test_put_watermark_missing_logo(self, mock_listdir, mock_exists):
        # Test put_watermark when Bosch logo is missing
        input_pdf = "input_folder"
        output_pdf = "output_folder"
        bosch_logo = "Bosch_logo.pdf"

        result = put_watermark(input_pdf, output_pdf, bosch_logo)
        self.assertEqual(result, 0)
        mock_exists.assert_called_with(bosch_logo)
    
    @patch("os.listdir", return_value=[])
    def test_put_watermark_no_input_file(self, mock_listdir):
        # Test put_watermark when no input file exists
        input_pdf = "input_folder"
        output_pdf = "output_folder"
        bosch_logo = r"Files\Files_footer\Bosch_logo.pdf"

        result = put_watermark(input_pdf, output_pdf, bosch_logo)
        self.assertEqual(result, 0)
        mock_listdir.assert_called_once_with(input_pdf)


if __name__ == "__main__":
    unittest.main()
