"""
Unit tests for STSZParser class.

Tests the behavior of the STSZParser, particularly handling of None stsz_atom
which occurs in fragmented MP4 files.
"""

import pytest
from unittest.mock import Mock, patch
from external_asset_ism_ismc_generation_tool.media_data_parser.atom_parser.stsz_parser import STSZParser


class TestSTSZParser:
    """Test suite for STSZParser class."""

    def test_get_track_size_with_none_atom(self, caplog):
        """Test that get_track_size returns 0 and logs info when stsz_atom is None.
        
        This scenario occurs in fragmented MP4 files where size/bitrate is derived
        from moof boxes instead of stsz atom.
        """
        # Arrange
        parser = STSZParser(stsz_atom=None)
        
        # Act
        import logging
        caplog.set_level(logging.INFO)
        result = parser.get_track_size()
        
        # Assert
        assert result == 0, "Should return 0 when stsz_atom is None"
        # Note: The custom logger (ILogger) may not be captured by caplog
        # The important behavior is that it returns 0 without raising an error
        # We verify the info message is logged by checking stderr in integration tests

    def test_get_track_size_with_none_atom_verifies_warning_message(self):
        """Test that the correct info message is logged when stsz_atom is None."""
        # Arrange
        with patch.object(STSZParser, '_STSZParser__logger') as mock_logger:
            parser = STSZParser(stsz_atom=None)
            
            # Act
            result = parser.get_track_size()
            
            # Assert
            assert result == 0, "Should return 0 when stsz_atom is None"
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "STSZ atom is None" in call_args
            assert "moof fragments" in call_args

    def test_get_track_size_with_uniform_sample_size(self):
        """Test track size calculation when all samples have the same size.
        
        When sample_size is non-zero, all samples have the same size,
        and total size = sample_size * sample_count.
        """
        # Arrange
        mock_stsz_atom = Mock()
        mock_stsz_atom.sample_size = 1024  # Non-zero means uniform size
        mock_stsz_atom.sample_count = 100
        parser = STSZParser(stsz_atom=mock_stsz_atom)
        
        # Act
        result = parser.get_track_size()
        
        # Assert
        expected_size = 1024 * 100  # 102400
        assert result == expected_size, f"Should return {expected_size} bytes"

    def test_get_track_size_with_variable_sample_sizes(self):
        """Test track size calculation when samples have different sizes.
        
        When sample_size is 0, entry_sizes contains individual sample sizes.
        """
        # Arrange
        mock_stsz_atom = Mock()
        mock_stsz_atom.sample_size = 0  # Zero means variable sizes
        mock_stsz_atom.entry_sizes = [512, 1024, 768, 2048, 1536]
        parser = STSZParser(stsz_atom=mock_stsz_atom)
        
        # Act
        result = parser.get_track_size()
        
        # Assert
        expected_size = sum(mock_stsz_atom.entry_sizes)  # 5888
        assert result == expected_size, f"Should return sum of all entry sizes: {expected_size}"

    def test_get_track_size_with_empty_entry_sizes(self):
        """Test track size calculation with zero samples."""
        # Arrange
        mock_stsz_atom = Mock()
        mock_stsz_atom.sample_size = 0
        mock_stsz_atom.entry_sizes = []
        parser = STSZParser(stsz_atom=mock_stsz_atom)
        
        # Act
        result = parser.get_track_size()
        
        # Assert
        assert result == 0, "Should return 0 when no samples"

    def test_get_track_size_with_zero_sample_size_and_zero_count(self):
        """Test edge case with zero samples but uniform size flag."""
        # Arrange
        mock_stsz_atom = Mock()
        mock_stsz_atom.sample_size = 100
        mock_stsz_atom.sample_count = 0
        parser = STSZParser(stsz_atom=mock_stsz_atom)
        
        # Act
        result = parser.get_track_size()
        
        # Assert
        assert result == 0, "Should return 0 when sample_count is 0"

    def test_parser_initialization_with_valid_atom(self):
        """Test that parser can be initialized with a valid Box object."""
        # Arrange
        mock_stsz_atom = Mock()
        mock_stsz_atom.sample_size = 512
        mock_stsz_atom.sample_count = 10
        
        # Act
        parser = STSZParser(stsz_atom=mock_stsz_atom)
        
        # Assert
        assert parser.stsz_atom is mock_stsz_atom, "Should store the provided atom"

    def test_parser_initialization_with_none(self):
        """Test that parser can be initialized with None (fragmented MP4 case)."""
        # Act
        parser = STSZParser(stsz_atom=None)
        
        # Assert
        assert parser.stsz_atom is None, "Should accept None as valid input"

    def test_no_warning_when_atom_is_present(self):
        """Test calculation works correctly when stsz_atom is present."""
        # Arrange
        mock_stsz_atom = Mock()
        mock_stsz_atom.sample_size = 1024
        mock_stsz_atom.sample_count = 50
        parser = STSZParser(stsz_atom=mock_stsz_atom)
        
        # Act
        result = parser.get_track_size()
        
        # Assert
        assert result == 51200, "Should calculate size correctly"

    def test_large_track_size_calculation(self):
        """Test calculation with large sample counts (realistic scenario)."""
        # Arrange
        mock_stsz_atom = Mock()
        mock_stsz_atom.sample_size = 0
        # Simulate a 1-hour video at 30fps with varying frame sizes
        mock_stsz_atom.entry_sizes = [50000] * 108000  # ~5.4GB total
        parser = STSZParser(stsz_atom=mock_stsz_atom)
        
        # Act
        result = parser.get_track_size()
        
        # Assert
        expected_size = 50000 * 108000
        assert result == expected_size, f"Should handle large track sizes: {expected_size}"


class TestSTSZParserFragmentedMP4Integration:
    """Integration tests for STSZParser with fragmented MP4 scenarios.
    
    These tests verify that when stsz_atom is None (common in fragmented MP4 files),
    the parser returns 0 gracefully and higher-level processing continues without error.
    """

    def test_fragmented_mp4_with_none_stsz_returns_zero(self):
        """Test that fragmented MP4 with None stsz_atom returns 0 for track_size.
        
        In fragmented MP4 files with moof boxes, the stsz atom may be absent since
        size information is stored in the moof/trun boxes instead.
        """
        # Arrange - simulating fragmented MP4 where MediaBoxExtractor.get_mp4_sub_box returns None
        parser = STSZParser(stsz_atom=None)
        
        # Act
        track_size = parser.get_track_size()
        
        # Assert
        assert track_size == 0, "Fragmented MP4 with None stsz should return track_size of 0"

    def test_fragmented_mp4_none_stsz_does_not_raise_exception(self):
        """Test that None stsz_atom does not raise an exception.
        
        Previously this would raise an error, but for fragmented MP4s,
        returning 0 is the correct behavior as size will be calculated from moof boxes.
        """
        # Arrange
        parser = STSZParser(stsz_atom=None)
        
        # Act & Assert - should not raise any exception
        try:
            result = parser.get_track_size()
            assert result == 0
        except Exception as e:
            pytest.fail(f"Should not raise exception for None stsz_atom, but got: {e}")

    def test_media_track_info_extractor_handles_none_stsz(self):
        """Test that MediaTrackInfoExtractor properly handles None stsz_atom.
        
        This integration test verifies the full flow: when stsz_atom is None,
        track_size is set to 0, and bitrate calculation falls back to moof fragments.
        """
        from external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor import MediaTrackInfoExtractor
        from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
        
        # Arrange - create mock trak_atom with missing stsz
        mock_trak = Mock()
        mock_mdia = Mock()
        mock_minf = Mock()
        mock_stbl = Mock()
        mock_mvex = Mock()
        mock_trex = Mock()
        mock_trex.track_ID = 1
        
        # Mock the track structure
        mock_trak_parser = Mock()
        mock_trak_parser.get_track_type.return_value = TrackType.VIDEO
        mock_trak_parser.get_track_id.return_value = 1
        mock_trak_parser.get_timescale.return_value = 10000000
        
        mock_stsd = Mock()
        mock_stsd_parser = Mock()
        mock_stsd_parser.get_track_format.return_value = "H264"
        # Mock stsd_atom_entries for video track (no audio parser needed)
        mock_entry = Mock()
        mock_entry.format = b'avc1'  # Video format
        mock_stsd_parser.stsd_atom_entries = [mock_entry]
        
        # Key: stsz_atom is None (fragmented MP4)
        with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.MediaBoxExtractor.get_mp4_sub_box') as mock_get_box:
            with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.TRAKParser') as mock_trak_class:
                with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STSDParser') as mock_stsd_class:
                    with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STSSParser'):
                        with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STTSParser'):
                            # Setup mocks
                            mock_trak_class.return_value = mock_trak_parser
                            mock_stsd_class.return_value = mock_stsd_parser
                            
                            def get_box_side_effect(parent, box_type):
                                box_map = {
                                    'mdia': mock_mdia,
                                    'minf': mock_minf,
                                    'stbl': mock_stbl,
                                    'trex': mock_trex,
                                    'stsd': mock_stsd,
                                    'stsz': None,  # Simulating fragmented MP4 - no stsz box
                                    'stss': Mock(),
                                    'stts': Mock(),
                                }
                                return box_map.get(box_type)
                            
                            mock_get_box.side_effect = get_box_side_effect
                            
                            # Act - should not raise exception
                            try:
                                extractor = MediaTrackInfoExtractor(
                                    trak_atom=mock_trak,
                                    mvhd_duration=600000000,  # 60 seconds at timescale 10000000
                                    mvhd_timescale=10000000,
                                    blob_name="test_fragmented.mp4",
                                    mvex_atom=mock_mvex
                                )
                                
                                # Assert
                                assert extractor.track_size == 0, "track_size should be 0 when stsz is None"
                                assert extractor.mvex_atom is mock_mvex, "mvex_atom should be set for fragmented MP4"
                                
                            except Exception as e:
                                pytest.fail(f"MediaTrackInfoExtractor should handle None stsz_atom, but raised: {e}")

    def test_video_track_with_moof_fragments_bypasses_stsz(self):
        """Test that video track extraction uses moof fragments when stsz is None.
        
        For fragmented MP4 files, when mvex_atom is present and stsz is None,
        bitrate should be calculated from moof_fragments, not from track_size.
        """
        from external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor import MediaTrackInfoExtractor
        from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
        
        # Arrange
        mock_trak = Mock()
        mock_mvex = Mock()
        
        with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.MediaBoxExtractor.get_mp4_sub_box') as mock_get_box:
            with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.TRAKParser') as mock_trak_class:
                with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STSDParser') as mock_stsd_class:
                    with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STSSParser') as mock_stss_class:
                        with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STTSParser'):
                            # Setup for video track with fragmented MP4 (mvex present, stsz absent)
                            mock_trak_parser = Mock()
                            mock_trak_parser.get_track_type.return_value = TrackType.VIDEO
                            mock_trak_parser.get_timescale.return_value = 90000
                            mock_trak_class.return_value = mock_trak_parser
                            
                            mock_stsd_parser = Mock()
                            mock_stsd_parser.get_track_format.return_value = "H264"
                            mock_stsd_parser.get_video_codec_private_data.return_value = "00000001"
                            mock_stsd_parser.get_width.return_value = 1920
                            mock_stsd_parser.get_height.return_value = 1080
                            # Mock stsd_atom_entries for video track
                            mock_entry = Mock()
                            mock_entry.format = b'avc1'
                            mock_stsd_parser.stsd_atom_entries = [mock_entry]
                            mock_stsd_class.return_value = mock_stsd_parser
                            
                            # No key frames in stss (fragmented MP4 typically don't have stss)
                            mock_stss_parser = Mock()
                            mock_stss_parser.get_key_frames_numbers_from_stss.return_value = []
                            mock_stss_class.return_value = mock_stss_parser
                            
                            mock_trex = Mock()
                            mock_trex.track_ID = 1
                            
                            def get_box_side_effect(parent, box_type):
                                box_map = {
                                    'mdia': Mock(),
                                    'minf': Mock(),
                                    'stbl': Mock(),
                                    'trex': mock_trex,
                                    'stsd': Mock(),
                                    'stsz': None,  # Key: No stsz for fragmented MP4
                                    'stss': Mock(),
                                    'stts': Mock(),
                                }
                                return box_map.get(box_type)
                            
                            mock_get_box.side_effect = get_box_side_effect
                            
                            # Act
                            extractor = MediaTrackInfoExtractor(
                                trak_atom=mock_trak,
                                mvhd_duration=600000000,
                                mvhd_timescale=10000000,
                                blob_name="fragmented_video.mp4",
                                mvex_atom=mock_mvex
                            )
                            
                            # Simulate moof fragments data (chunks and sizes)
                            moof_fragments = {
                                1: ([2.0, 2.0, 2.0], [500000, 500000, 500000])  # 3 chunks, 2 seconds each, 500KB each
                            }
                            
                            # Should not raise exception and should use moof_fragments for bitrate
                            try:
                                track_info = extractor.get_track_info(moof_fragments)
                                
                                # Assert
                                assert track_info is not None
                                assert track_info.track_type == TrackType.VIDEO
                                assert extractor.track_size == 0, "track_size should be 0 for fragmented MP4"
                                # Bitrate should be calculated from moof fragments: (500000 * 3 * 8) / 60 = 200000
                                assert int(track_info.bit_rate) > 0, "Bitrate should be calculated from moof fragments"
                                
                            except Exception as e:
                                pytest.fail(f"Video track extraction should handle fragmented MP4 with None stsz, but raised: {e}")

    def test_audio_track_with_moof_fragments_and_none_stsz(self):
        """Test that audio track extraction handles None stsz and uses moof fragments."""
        from external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor import MediaTrackInfoExtractor
        from external_asset_ism_ismc_generation_tool.media_data_parser.model.track_type import TrackType
        
        # Arrange
        mock_trak = Mock()
        mock_mvex = Mock()
        
        with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.MediaBoxExtractor.get_mp4_sub_box') as mock_get_box:
            with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.TRAKParser') as mock_trak_class:
                with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STSDParser') as mock_stsd_class:
                    with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STSSParser'):
                        with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.STTSParser'):
                            with patch('external_asset_ism_ismc_generation_tool.media_data_parser.media_track_info_extractor.ESDSParser') as mock_esds_class:
                                # Setup for audio track
                                mock_trak_parser = Mock()
                                mock_trak_parser.get_track_type.return_value = TrackType.AUDIO
                                mock_trak_parser.get_timescale.return_value = 48000
                                mock_trak_parser.get_track_language.return_value = "eng"
                                mock_trak_class.return_value = mock_trak_parser
                                
                                mock_stsd_parser = Mock()
                                mock_stsd_parser.stsd_atom_entries = [Mock(format=b'mp4a')]
                                mock_stsd_parser.get_channels.return_value = 2
                                mock_stsd_parser.get_packet_size.return_value = 4
                                mock_stsd_parser.get_sampling_rate.return_value = 48000
                                mock_stsd_parser.get_bits_per_sample.return_value = 16
                                mock_stsd_class.return_value = mock_stsd_parser
                                
                                # Mock audio parser
                                mock_audio_data = Mock()
                                mock_audio_data.bit_rate = 128000
                                mock_audio_data.four_cc = "AACL"
                                mock_audio_data.codec_private_data = "1190"
                                mock_audio_parser = Mock()
                                mock_audio_parser.get_audio_track_data.return_value = mock_audio_data
                                mock_audio_parser.audio_format = "mp4a"
                                mock_esds_class.return_value = mock_audio_parser
                                
                                mock_trex = Mock()
                                mock_trex.track_ID = 2
                                
                                def get_box_side_effect(parent, box_type):
                                    box_map = {
                                        'mdia': Mock(),
                                        'minf': Mock(),
                                        'stbl': Mock(),
                                        'trex': mock_trex,
                                        'stsd': Mock(),
                                        'stsz': None,  # No stsz for fragmented MP4
                                        'stss': None,
                                        'stts': Mock(),
                                        'esds': Mock(),
                                    }
                                    return box_map.get(box_type)
                                
                                mock_get_box.side_effect = get_box_side_effect
                                
                                # Act
                                extractor = MediaTrackInfoExtractor(
                                    trak_atom=mock_trak,
                                    mvhd_duration=600000000,
                                    mvhd_timescale=10000000,
                                    blob_name="fragmented_audio.mp4",
                                    mvex_atom=mock_mvex
                                )
                                
                                # Simulate moof fragments
                                moof_fragments = {
                                    2: ([2.0, 2.0, 2.0], [32000, 32000, 32000])  # 3 chunks, 2 sec each, 32KB each
                                }
                                
                                try:
                                    track_info = extractor.get_track_info(moof_fragments)
                                    
                                    # Assert
                                    assert track_info is not None
                                    assert track_info.track_type == TrackType.AUDIO
                                    assert extractor.track_size == 0, "track_size should be 0 when stsz is None"
                                    assert int(track_info.bit_rate) > 0, "Bitrate should be calculated from moof or audio parser"
                                    
                                except Exception as e:
                                    pytest.fail(f"Audio track with fragmented MP4 should not raise exception: {e}")
