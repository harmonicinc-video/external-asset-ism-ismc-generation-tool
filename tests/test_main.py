"""
Simple test for main.py functions
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import convert_vtt_to_cmft, generate_manifests_local_use, generate_manifests_azure_use
from external_asset_ism_ismc_generation_tool.text_data_parser.model.conversion_summary import ConversionSummary


class TestConvertVttToCmft:
    """Test VTT to CMFT conversion function"""
    
    @patch('main.VttToCmftConverter')
    @patch('main.LocalFileServiceClient')
    def test_convert_vtt_to_cmft_local_mode(self, mock_local_client, mock_converter):
        """Test VTT conversion in local mode"""
        # Setup
        settings = {'local_directory': '/test/path'}
        
        # Mock the converter to return a summary
        mock_summary = ConversionSummary()
        mock_summary.total = 2
        mock_summary.successful = 2
        mock_converter.convert_vtt_files_in_container.return_value = mock_summary
        
        # Execute
        result = convert_vtt_to_cmft(settings, use_local=True)
        
        # Verify
        assert result.total == 2
        assert result.successful == 2
        mock_local_client.assert_called_once_with(settings)
    
    @patch('main.VttToCmftConverter')
    @patch('main.AzureBlobServiceClient')
    def test_convert_vtt_to_cmft_azure_mode(self, mock_azure_client, mock_converter):
        """Test VTT conversion in Azure mode"""
        # Setup
        settings = {'azure_connection': 'test'}
        
        # Mock the converter to return a summary
        mock_summary = ConversionSummary()
        mock_summary.total = 1
        mock_summary.successful = 1
        mock_converter.convert_vtt_files_in_container.return_value = mock_summary
        
        # Execute
        result = convert_vtt_to_cmft(settings)
        
        # Verify
        assert result.total == 1
        assert result.successful == 1
        mock_azure_client.assert_called_once_with(settings)
    
    @patch('main.VttToCmftConverter')
    @patch('main.LocalFileServiceClient')
    def test_convert_vtt_to_cmft_error_handling(self, mock_local_client, mock_converter):
        """Test error handling in VTT conversion"""
        # Setup
        settings = {'local_directory': '/test/path'}
        mock_converter.convert_vtt_files_in_container.side_effect = Exception("Test error")
        
        # Execute
        result = convert_vtt_to_cmft(settings, use_local=True)
        
        # Verify - should return empty summary on error
        assert result.total == 0
        assert result.successful == 0


class TestGenerateManifestsLocal:
    """Test local manifest generation"""
    
    @patch('main.IsmcGenerator')
    @patch('main.IsmGenerator')
    @patch('main.MediaDataParser')
    @patch('main.LocalDataHandler')
    @patch('main.LocalFileServiceClient')
    def test_generate_manifests_local_use(
        self, 
        mock_local_client, 
        mock_local_handler, 
        mock_media_parser,
        mock_ism_gen,
        mock_ismc_gen
    ):
        """Test manifest generation in local mode"""
        # Setup
        settings = {'local_directory': '/test/path'}
        
        # Mock LocalFileServiceClient
        mock_client_instance = Mock()
        mock_client_instance.local_directory = '/test/path'
        mock_client_instance.write_file = Mock()
        mock_local_client.return_value = mock_client_instance
        
        # Mock BlobMediaData
        mock_blob_data = Mock()
        mock_blob_data.manifest_name = 'test_manifest'
        mock_blob_data.media_datas = []
        mock_blob_data.media_index_datas = []
        mock_blob_data.text_data_info_list = []
        mock_local_handler.get_data_from_local_files.return_value = mock_blob_data
        
        # Mock MediaData
        mock_media = Mock()
        mock_media.media_track_info_list = []
        mock_media.media_duration = 1000
        mock_media_parser.get_media_data.return_value = mock_media
        
        # Mock generators
        mock_ism_gen.get_audios.return_value = []
        mock_ism_gen.get_videos.return_value = []
        mock_ism_gen.get_text_streams.return_value = []
        mock_ism_gen.generate.return_value = '<ism>xml content</ism>'
        mock_ismc_gen.generate.return_value = '<ismc>xml content</ismc>'
        
        # Execute
        result = generate_manifests_local_use(settings)
        
        # Verify
        assert result.manifest_name == 'test_manifest'
        assert result.ism_created is True
        assert result.ismc_created is True
        assert mock_client_instance.write_file.call_count == 2


class TestGenerateManifestsAzure:
    """Test Azure manifest generation"""
    
    @patch('main.IsmcGenerator')
    @patch('main.IsmGenerator')
    @patch('main.MediaDataParser')
    @patch('main.BlobDataHandler')
    @patch('main.AzureBlobServiceClient')
    def test_generate_manifests_azure_use(
        self, 
        mock_azure_client, 
        mock_blob_handler, 
        mock_media_parser,
        mock_ism_gen,
        mock_ismc_gen
    ):
        """Test manifest generation in Azure mode"""
        # Setup
        settings = {'azure_connection': 'test'}
        
        # Mock AzureBlobServiceClient
        mock_client_instance = Mock()
        mock_client_instance.container_client.container_name = 'test-container'
        mock_client_instance.blob_exists.return_value = False
        mock_client_instance.upload_blob_to_container = Mock()
        mock_azure_client.return_value = mock_client_instance
        
        # Mock BlobMediaData
        mock_blob_data = Mock()
        mock_blob_data.manifest_name = 'test_manifest'
        mock_blob_data.media_datas = []
        mock_blob_data.media_index_datas = []
        mock_blob_data.text_data_info_list = []
        mock_blob_handler.get_data_from_blobs.return_value = mock_blob_data
        
        # Mock MediaData
        mock_media = Mock()
        mock_media.media_track_info_list = []
        mock_media.media_duration = 1000
        mock_media_parser.get_media_data.return_value = mock_media
        
        # Mock generators
        mock_ism_gen.get_audios.return_value = []
        mock_ism_gen.get_videos.return_value = []
        mock_ism_gen.get_text_streams.return_value = []
        mock_ism_gen.generate.return_value = '<ism>xml content</ism>'
        mock_ismc_gen.generate.return_value = '<ismc>xml content</ismc>'
        
        # Execute
        result = generate_manifests_azure_use(settings)
        
        # Verify
        assert result.manifest_name == 'test_manifest'
        assert result.ism_created is True
        assert result.ismc_created is True
        assert mock_client_instance.upload_blob_to_container.call_count == 2
    
    @patch('main.IsmcGenerator')
    @patch('main.IsmGenerator')
    @patch('main.MediaDataParser')
    @patch('main.BlobDataHandler')
    @patch('main.AzureBlobServiceClient')
    def test_generate_manifests_azure_existing_files(
        self, 
        mock_azure_client, 
        mock_blob_handler, 
        mock_media_parser,
        mock_ism_gen,
        mock_ismc_gen
    ):
        """Test manifest generation when files already exist"""
        # Setup
        settings = {'azure_connection': 'test'}
        
        # Mock AzureBlobServiceClient - files exist
        mock_client_instance = Mock()
        mock_client_instance.container_client.container_name = 'test-container'
        mock_client_instance.blob_exists.return_value = True  # Files exist
        mock_client_instance.upload_blob_to_container = Mock()
        mock_azure_client.return_value = mock_client_instance
        
        # Mock BlobMediaData
        mock_blob_data = Mock()
        mock_blob_data.manifest_name = 'test_manifest'
        mock_blob_data.media_datas = []
        mock_blob_data.media_index_datas = []
        mock_blob_data.text_data_info_list = []
        mock_blob_handler.get_data_from_blobs.return_value = mock_blob_data
        
        # Mock MediaData
        mock_media = Mock()
        mock_media.media_track_info_list = []
        mock_media.media_duration = 1000
        mock_media_parser.get_media_data.return_value = mock_media
        
        # Mock generators
        mock_ism_gen.get_audios.return_value = []
        mock_ism_gen.get_videos.return_value = []
        mock_ism_gen.get_text_streams.return_value = []
        mock_ism_gen.generate.return_value = '<ism>xml content</ism>'
        mock_ismc_gen.generate.return_value = '<ismc>xml content</ismc>'
        
        # Execute
        result = generate_manifests_azure_use(settings)
        
        # Verify - should create files with '_new' suffix
        assert result.ism_created is True
        assert result.ismc_created is True
        
        # Check that upload was called with '_new' suffix
        upload_calls = mock_client_instance.upload_blob_to_container.call_args_list
        assert 'test_manifest_new.ism' in upload_calls[0][0]
        assert 'test_manifest_new.ismc' in upload_calls[1][0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
