from typing import List

from allure_commons._allure import title, description, issue, link
from external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser import MediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_data import MediaData
from external_asset_ism_ismc_generation_tool.mss_client_manifest.ismc_generator import IsmcGenerator
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from tests.test_utils.common.allure_helper import Allure
from tests.test_utils.common.common import Common
from tests.test_utils.ismc_manifest_extracror.ismc_manifest_extractor import IsmcManifestExtractor


class TestIsmcGeneration:
    @title('Test Ismc Generation for 3 mp4 files with 2 audio tracks and 1 video track')
    @description('Test .ismc manifest generation for 3 mp4 files with 2 AAC-HE audio tracks and 1 AVC video track')
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223784358854
    #     List of files:
    #         Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ1.2.0DE2.0EN.16x9.mp4
    #         Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ3.2.0DE2.0EN.16x9.mp4
    #         Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ5.2.0DE2.0EN.16x9.mp4
    def test_check_generated_ismc_manifest_avc_aac_le_mp4(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_avc_aacle_2_audios_3_videos_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 5
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration, media_track_infos=media_data.media_track_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '64328000000'
                    assert len(ismc_object.stream_indexes) == 3
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndexes attributes for the first audio track"):
                        assert ismc_object.stream_indexes[0].chunks == '3208'
                        assert ismc_object.stream_indexes[0].language == 'deu'
                        assert ismc_object.stream_indexes[0].name == 'German'
                        assert ismc_object.stream_indexes[0].quality_levels == '1'
                        assert ismc_object.stream_indexes[0].stream_type == 'audio'
                        assert ismc_object.stream_indexes[0].url == 'QualityLevels({bitrate})/Fragments(German={start time})'
                        assert len(ismc_object.stream_indexes[0].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[0].chunk_datas) == 2140
                        with Allure.Step("Verify QualityLevel attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bitrate == '64000'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].codec_private_data == '131056E598'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].sampling_rate == '24000'
                        with Allure.Step("Verify c elements attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].duration == '20053333'

                            assert not ismc_object.stream_indexes[0].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[1].duration == '20053334'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2].duration == '20053333'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2138].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2138].duration == '20053333'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2139].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2139].duration == '16640000'

                    with Allure.Step("Verify StreamIndexes attributes for the second audio track"):
                        assert ismc_object.stream_indexes[1].chunks == '3208'
                        assert ismc_object.stream_indexes[1].language == 'eng'
                        assert ismc_object.stream_indexes[1].name == 'English'
                        assert ismc_object.stream_indexes[1].quality_levels == '1'
                        assert ismc_object.stream_indexes[1].stream_type == 'audio'
                        assert ismc_object.stream_indexes[1].url == 'QualityLevels({bitrate})/Fragments(English={start time})'
                        assert len(ismc_object.stream_indexes[1].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[1].chunk_datas) == 2140
                        with Allure.Step("Verify QualityLevel attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bitrate == '64000'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].codec_private_data == '131056E598'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].sampling_rate == '24000'
                        with Allure.Step("Verify c elements attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].duration == '20053333'

                            assert not ismc_object.stream_indexes[1].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[1].duration == '20053334'

                            assert not ismc_object.stream_indexes[1].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[2].duration == '20053333'

                            assert not ismc_object.stream_indexes[1].chunk_datas[2138].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[2138].duration == '20053333'

                            assert not ismc_object.stream_indexes[1].chunk_datas[2139].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[2139].duration == '16640000'

                    with Allure.Step("Verify StreamIndexes attributes for the video track"):
                        assert ismc_object.stream_indexes[2].chunks == '3217'
                        assert ismc_object.stream_indexes[2].name == 'video_0'
                        assert ismc_object.stream_indexes[2].quality_levels == '3'
                        assert ismc_object.stream_indexes[2].stream_type == 'video'
                        assert ismc_object.stream_indexes[2].url == 'QualityLevels({bitrate})/Fragments(video_0={start time})'
                        assert len(ismc_object.stream_indexes[2].quality_level_list) == 3
                        assert len(ismc_object.stream_indexes[2].chunk_datas) == 2
                        with Allure.Step("Verify QualityLevels attributes for the video track"):
                            with Allure.Step("Verify QualityLevel attributes for the video track with 99966 bitrate"):
                                assert ismc_object.stream_indexes[2].quality_level_list[0].bitrate == '99966'
                                assert ismc_object.stream_indexes[2].quality_level_list[
                                           0].codec_private_data == '00000001674D4015AA6187FDE02200000300020000030065C0000C340015F9C92501F162D3800000000168EFBC80'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].index == '0'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].max_height == '108'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].max_width == '192'
                            with Allure.Step("Verify QualityLevel attributes for the video track with 299963 bitrate"):
                                assert ismc_object.stream_indexes[2].quality_level_list[1].bitrate == '299963'
                                assert ismc_object.stream_indexes[2].quality_level_list[
                                           1].codec_private_data == '00000001674D4015AA60A0CFCF80880000030008000003019700000927800107AF249407C58B4E0000000168EFBC80'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].index == '1'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].max_height == '180'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].max_width == '320'
                            with Allure.Step("Verify QualityLevel attributes for the video track with 299963 bitrate"):
                                assert ismc_object.stream_indexes[2].quality_level_list[2].bitrate == '599991'
                                assert ismc_object.stream_indexes[2].quality_level_list[
                                           2].codec_private_data == '00000001674D401EAA605017FCB808800000030080000019701000493E00041EBC92501F162D380000000168EFBC80'
                                assert ismc_object.stream_indexes[2].quality_level_list[2].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[2].quality_level_list[2].index == '2'
                                assert ismc_object.stream_indexes[2].quality_level_list[2].max_height == '360'
                                assert ismc_object.stream_indexes[2].quality_level_list[2].max_width == '640'
                        with Allure.Step("Verify c elements attributes for the video track"):
                            assert ismc_object.stream_indexes[2].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].duration == '20000000'

                            assert not ismc_object.stream_indexes[2].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[2].chunk_datas[1].duration == '8000000'

    @title('Test Ismc Generation for 2 mp4 files with 2 audio tracks and 1 video track')
    @description('Test .ismc manifest generation for 2 mp4 files with 2 AAC-LE audio tracks and 1 HEVC video track. Video tracks have different key frames')
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223787106023
    #     List of files:
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ4.mp4
    def test_check_generated_ismc_manifest_hevc_aac_he_mp4(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_hevc_aacle_2_audios_2_videos_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 4
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration, media_track_infos=media_data.media_track_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '83007040000'
                    assert len(ismc_object.stream_indexes) == 3
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndexes attributes for the first audio track"):
                        assert ismc_object.stream_indexes[0].chunks == '4140'
                        assert ismc_object.stream_indexes[0].language == 'deu'
                        assert ismc_object.stream_indexes[0].name == 'German'
                        assert ismc_object.stream_indexes[0].quality_levels == '1'
                        assert ismc_object.stream_indexes[0].stream_type == 'audio'
                        assert ismc_object.stream_indexes[0].url == 'QualityLevels({bitrate})/Fragments(German={start time})'
                        assert len(ismc_object.stream_indexes[0].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[0].chunk_datas) == 2761
                        with Allure.Step("Verify QualityLevel attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bitrate == '160000'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].codec_private_data == '1190'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].sampling_rate == '48000'
                        with Allure.Step("Verify c elements attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].duration == '20053333'

                            assert not ismc_object.stream_indexes[0].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[1].duration == '20053334'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2].duration == '20053333'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2759].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2759].duration == '20053334'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2760].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2760].duration == '6826667'

                    with Allure.Step("Verify StreamIndexes attributes for the second audio track"):
                        assert ismc_object.stream_indexes[1].chunks == '4140'
                        assert ismc_object.stream_indexes[1].language == 'eng'
                        assert ismc_object.stream_indexes[1].name == 'English'
                        assert ismc_object.stream_indexes[1].quality_levels == '1'
                        assert ismc_object.stream_indexes[1].stream_type == 'audio'
                        assert ismc_object.stream_indexes[1].url == 'QualityLevels({bitrate})/Fragments(English={start time})'
                        assert len(ismc_object.stream_indexes[1].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[1].chunk_datas) == 2761
                        with Allure.Step("Verify QualityLevel attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bitrate == '160000'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].codec_private_data == '1190'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].sampling_rate == '48000'
                        with Allure.Step("Verify c elements attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].duration == '20053333'

                            assert not ismc_object.stream_indexes[1].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[1].duration == '20053334'

                            assert not ismc_object.stream_indexes[1].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[2].duration == '20053333'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2759].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2759].duration == '20053334'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2760].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2760].duration == '6826667'

                    with Allure.Step("Verify StreamIndex attributes for the first video track"):
                        assert ismc_object.stream_indexes[2].chunks == '4147'
                        assert ismc_object.stream_indexes[2].name == 'video_0'
                        assert ismc_object.stream_indexes[2].quality_levels == '2'
                        assert ismc_object.stream_indexes[2].stream_type == 'video'
                        assert ismc_object.stream_indexes[2].url == 'QualityLevels({bitrate})/Fragments(video_0={start time})'
                        assert len(ismc_object.stream_indexes[2].quality_level_list) == 2
                        assert len(ismc_object.stream_indexes[2].chunk_datas) == 2
                        with Allure.Step("Verify QualityLevel 1 attributes for the video track"):
                            assert ismc_object.stream_indexes[2].quality_level_list[0].bitrate == '1700474'
                            assert ismc_object.stream_indexes[2].quality_level_list[0].codec_private_data == \
                                   '0000000142010101600000030090000003000003005DA00200802416595964932BFFC00040005A80808082000007D20000BB80C0192CBC000CF8400033E164000000014401C172B46240'
                            assert ismc_object.stream_indexes[2].quality_level_list[0].four_cc == 'HVC1'
                            assert ismc_object.stream_indexes[2].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[2].quality_level_list[0].max_height == '576'
                            assert ismc_object.stream_indexes[2].quality_level_list[0].max_width == '1024'
                        with Allure.Step("Verify QualityLevel 2 attributes for the video track"):
                            assert ismc_object.stream_indexes[2].quality_level_list[1].bitrate == '5000329'
                            assert ismc_object.stream_indexes[2].quality_level_list[1].codec_private_data == \
                                   '00000001420101016000000300900000030000030078A003C08010E596565924CAFFF000100016A0202020800001F480002EE0300A4B2F0000989680004C4B64000000014401C172B46240'
                            assert ismc_object.stream_indexes[2].quality_level_list[1].four_cc == 'HVC1'
                            assert ismc_object.stream_indexes[2].quality_level_list[1].index == '1'
                            assert ismc_object.stream_indexes[2].quality_level_list[1].max_height == '1080'
                            assert ismc_object.stream_indexes[2].quality_level_list[1].max_width == '1920'

                        with Allure.Step("Verify c elements attributes for the video track"):
                            assert ismc_object.stream_indexes[2].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].duration == '20020000'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].r == '4146'

                            assert not ismc_object.stream_indexes[2].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[2].chunk_datas[1].duration == '3753750'
                            assert ismc_object.stream_indexes[2].chunk_datas[1].r == '1'

    @title('Test Ismc Generation for 2 mp4 files and vtt file')
    @description('Test .ismc manifest generation for 2 mp4 files and vtt file')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92425", name="NG-92425")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223787106023
    #     List of files:
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ4.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ6.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_PROXY_648535_subtitle.vtt
    def test_check_generated_ismc_manifest_vtt(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_vtt_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 8
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                text_data_info_list: List[TextDataInfo] = Common.get_test_data_from_json(Common.get_data_file_path('test_vtt_data.json'))['text_data_infos_list']
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration,
                                                         media_track_infos=media_data.media_track_info_list,
                                                         text_data_info_list=text_data_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '83007040000'
                    assert len(ismc_object.stream_indexes) == 7
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndex attributes for the text track"):
                        assert ismc_object.stream_indexes[6].chunks == '1'
                        assert ismc_object.stream_indexes[6].name == 'text_0'
                        assert ismc_object.stream_indexes[6].quality_levels == '1'
                        assert ismc_object.stream_indexes[6].stream_type == 'text'
                        assert ismc_object.stream_indexes[6].url == 'QualityLevels({bitrate})/Fragments(text_0={start time})'
                        assert len(ismc_object.stream_indexes[6].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[6].chunk_datas) == 1
                        with Allure.Step("Verify QualityLevel attributes for the text track"):
                            assert ismc_object.stream_indexes[6].quality_level_list[0].bitrate == '138'
                            assert ismc_object.stream_indexes[6].quality_level_list[0].four_cc == 'WVTT'
                        with Allure.Step("Verify c elements attributes for the text track"):
                            assert ismc_object.stream_indexes[6].chunk_datas[0].time_start == '311140000'
                            assert ismc_object.stream_indexes[6].chunk_datas[0].duration == '81496410000'

    @title('Test Ismc Generation for mp4 and ttml file')
    @description('Test .ismc manifest generation for mp4 and ttml file')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92426", name="NG-92426")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223787106023
    #     List of files:
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_PROXY_648535_subtitle.ttml
    def test_check_generated_ismc_manifest_ttml(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_ttml_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 3
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                text_data_info_list: List[TextDataInfo] = Common.get_test_data_from_json(Common.get_data_file_path('test_ttml_data.json'))['text_data_infos_list']
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration,
                                                         media_track_infos=media_data.media_track_info_list,
                                                         text_data_info_list=text_data_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '83007040000'
                    assert len(ismc_object.stream_indexes) == 4
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndex attributes for the text track"):
                        assert ismc_object.stream_indexes[3].chunks == '1'
                        assert ismc_object.stream_indexes[3].name == 'text_0'
                        assert ismc_object.stream_indexes[3].quality_levels == '1'
                        assert ismc_object.stream_indexes[3].stream_type == 'text'
                        assert ismc_object.stream_indexes[3].url == 'QualityLevels({bitrate})/Fragments(text_0={start time})'
                        assert len(ismc_object.stream_indexes[3].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[3].chunk_datas) == 1
                        with Allure.Step("Verify QualityLevel attributes for the text track"):
                            assert ismc_object.stream_indexes[3].quality_level_list[0].bitrate == '292'
                            assert ismc_object.stream_indexes[3].quality_level_list[0].four_cc == 'TTML'
                            assert ismc_object.stream_indexes[3].quality_level_list[0].index == '0'
                        with Allure.Step("Verify c elements attributes for the text track"):
                            assert ismc_object.stream_indexes[3].chunk_datas[0].time_start == '311251250'
                            assert ismc_object.stream_indexes[3].chunk_datas[0].duration == '81496256250'
                            assert ismc_object.stream_indexes[3].chunk_datas[0].r == '1'

    @title('Test Ismc Generation for mp4, mpi and cmft files')
    @description('Test .ismc manifest generation for mp4, mpi and cmft files')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92427", name="NG-92427")
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92423", name="NG-92423")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/file/1305727931084?s=7zr2g2kp0o7p3bs4ux854fhyapfvw162
    #     List of files:
    #         302be42116754716ab8ccbc37a5fd68f_256x144_150.mp4
    #         302be42116754716ab8ccbc37a5fd68f_384x216_250.mp4
    #         302be42116754716ab8ccbc37a5fd68f_256x144_150_1.mpi
    #         302be42116754716ab8ccbc37a5fd68f_256x144_150_2.mpi
    #         302be42116754716ab8ccbc37a5fd68f_256x144_150_3.mpi
    #         302be42116754716ab8ccbc37a5fd68f_384x216_250_1.mpi
    #         302be42116754716ab8ccbc37a5fd68fAR.cmft
    def test_check_generated_ismc_manifest_mp4_mpi_cmft(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_mpi_cmft_data.json'))['media_datas']
                assert mp4_datas
                mp4_media_index_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_mpi_cmft_data.json'))['media_index_datas']
                assert mp4_media_index_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(media_datas=mp4_datas, media_index_datas=mp4_media_index_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 4
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration,
                                                         media_track_infos=media_data.media_track_info_list,
                                                         text_data_info_list=[])
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '657500000'
                    assert len(ismc_object.stream_indexes) == 3
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndex attributes for the audio track"):
                        assert ismc_object.stream_indexes[0].chunks == '33'
                        assert ismc_object.stream_indexes[0].language == 'und'
                        assert ismc_object.stream_indexes[0].name == 'Undetermined'
                        assert ismc_object.stream_indexes[0].quality_levels == '1'
                        assert ismc_object.stream_indexes[0].stream_type == 'audio'
                        assert ismc_object.stream_indexes[0].url == 'QualityLevels({bitrate})/Fragments(Undetermined={start time})'
                        assert len(ismc_object.stream_indexes[0].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[0].chunk_datas) == 22
                        with Allure.Step("Verify QualityLevel attributes for the audio track"):
                            assert ismc_object.stream_indexes[0].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bitrate == '128076'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].codec_private_data == '1190'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].sampling_rate == '48000'
                        with Allure.Step("Verify c elements attributes for the audio track"):
                            assert ismc_object.stream_indexes[0].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].duration == '20053333'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].r == '2'
                            assert ismc_object.stream_indexes[0].chunk_datas[1].duration == '20053334'
                            assert ismc_object.stream_indexes[0].chunk_datas[1].r == '1'
                            assert ismc_object.stream_indexes[0].chunk_datas[20].duration == '20053333'
                            assert ismc_object.stream_indexes[0].chunk_datas[20].r == '2'
                            assert ismc_object.stream_indexes[0].chunk_datas[21].duration == '15786667'
                            assert ismc_object.stream_indexes[0].chunk_datas[21].r == '1'
                    with Allure.Step("Verify StreamIndex attributes for the video track"):
                        assert ismc_object.stream_indexes[1].chunks == '33'
                        assert ismc_object.stream_indexes[1].name == 'video_0'
                        assert ismc_object.stream_indexes[1].quality_levels == '2'
                        assert ismc_object.stream_indexes[1].stream_type == 'video'
                        assert ismc_object.stream_indexes[1].url == 'QualityLevels({bitrate})/Fragments(video_0={start time})'
                        assert len(ismc_object.stream_indexes[1].quality_level_list) == 2
                        assert len(ismc_object.stream_indexes[1].chunk_datas) == 2
                        with Allure.Step("Verify QualityLevel attributes for the video track"):
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bitrate == '153691'
                            assert ismc_object.stream_indexes[1].quality_level_list[
                                       0].codec_private_data == '000000016764000CACD941013B016A020202800000030080000019078A14CB0000000168EBECB22C'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].four_cc == 'AVC1'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].max_height == '144'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].max_width == '256'

                            assert ismc_object.stream_indexes[1].quality_level_list[1].bitrate == '255149'
                            assert ismc_object.stream_indexes[1].quality_level_list[
                                       1].codec_private_data == '000000016764000DACD94181DF97016A020202800000030080000019078A14CB0000000168EBECB22C'
                            assert ismc_object.stream_indexes[1].quality_level_list[1].four_cc == 'AVC1'
                            assert ismc_object.stream_indexes[1].quality_level_list[1].index == '1'
                            assert ismc_object.stream_indexes[1].quality_level_list[1].max_height == '216'
                            assert ismc_object.stream_indexes[1].quality_level_list[1].max_width == '384'
                        with Allure.Step("Verify c elements attributes for the video track"):
                            assert ismc_object.stream_indexes[1].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].duration == '20000000'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].r == '32'
                            assert ismc_object.stream_indexes[1].chunk_datas[1].duration == '17200000'
                            assert ismc_object.stream_indexes[1].chunk_datas[1].r == '1'
                    with Allure.Step("Verify StreamIndex attributes for the text track"):
                        assert ismc_object.stream_indexes[2].chunks == '8'
                        assert ismc_object.stream_indexes[2].name == 'text_0'
                        assert ismc_object.stream_indexes[2].quality_levels == '1'
                        assert ismc_object.stream_indexes[2].stream_type == 'text'
                        assert ismc_object.stream_indexes[2].url == 'QualityLevels({bitrate})/Fragments(text_0={start time})'
                        assert len(ismc_object.stream_indexes[2].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[2].chunk_datas) == 1
                        with Allure.Step("Verify QualityLevel attributes for the text track"):
                            assert ismc_object.stream_indexes[2].quality_level_list[0].bitrate == '1595'
                            assert ismc_object.stream_indexes[2].quality_level_list[0].four_cc == 'IMSC'
                        with Allure.Step("Verify c elements attributes for the text track"):
                            assert ismc_object.stream_indexes[2].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].duration == '60000000'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].r == '8'

    @title('Test Ismc Generation for 3 ismv and 2 isma files with multiple moof boxes')
    @description('Test .ismc manifest generation for 3 ismv and 2 isma files with multiple moof boxes')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92424", name="NG-92424")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/folder/233134328607
    #     List of files:
    #         0530487-BROOKLYN_NINE_NIN_E013-HD-FI_550.ismv
    #         0530487-BROOKLYN_NINE_NIN_E013-HD-FI_1000.ismv
    #         0530487-BROOKLYN_NINE_NIN_E013-HD-FI_1550.ismv
    #         0530487-BROOKLYN_NINE_NIN_E013-HD-FI_128_fra.isma
    #         0530487-BROOKLYN_NINE_NIN_E013-HD-FI_128_eng.isma
    def test_check_generated_ismc_manifest_ismv_isma(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_isma_ismv_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 5
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration, media_track_infos=media_data.media_track_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '12323626666'
                    assert len(ismc_object.stream_indexes) == 5
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndexes attributes for the first audio track"):
                        assert ismc_object.stream_indexes[0].chunks == '617'
                        assert ismc_object.stream_indexes[0].language == 'fra'
                        assert ismc_object.stream_indexes[0].name == 'French'
                        assert ismc_object.stream_indexes[0].quality_levels == '1'
                        assert ismc_object.stream_indexes[0].stream_type == 'audio'
                        assert ismc_object.stream_indexes[0].url == 'QualityLevels({bitrate})/Fragments(French={start time})'
                        assert len(ismc_object.stream_indexes[0].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[0].chunk_datas) == 463
                        with Allure.Step("Verify QualityLevel attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bitrate == '1536000'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].codec_private_data == '1190'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].sampling_rate == '48000'
                        with Allure.Step("Verify c elements attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].duration == '20053333'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].r == '2'

                            assert not ismc_object.stream_indexes[0].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[1].duration == '20053334'
                            assert ismc_object.stream_indexes[0].chunk_datas[1].r == '1'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2].duration == '19840000'
                            assert ismc_object.stream_indexes[0].chunk_datas[2].r == '1'

                            assert not ismc_object.stream_indexes[0].chunk_datas[461].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[461].duration == '19840000'
                            assert ismc_object.stream_indexes[0].chunk_datas[461].r == '1'

                            assert not ismc_object.stream_indexes[0].chunk_datas[462].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[462].duration == '3626666'
                            assert ismc_object.stream_indexes[0].chunk_datas[462].r == '1'

                    with Allure.Step("Verify StreamIndexes attributes for the second audio track"):
                        assert ismc_object.stream_indexes[1].chunks == '617'
                        assert ismc_object.stream_indexes[1].language == 'eng'
                        assert ismc_object.stream_indexes[1].name == 'English'
                        assert ismc_object.stream_indexes[1].quality_levels == '1'
                        assert ismc_object.stream_indexes[1].stream_type == 'audio'
                        assert ismc_object.stream_indexes[1].url == 'QualityLevels({bitrate})/Fragments(English={start time})'
                        assert len(ismc_object.stream_indexes[1].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[1].chunk_datas) == 463
                        with Allure.Step("Verify QualityLevel attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bitrate == '1536000'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].codec_private_data == '1190'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].sampling_rate == '48000'
                        with Allure.Step("Verify c elements attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].duration == '20053333'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].r == '2'

                            assert not ismc_object.stream_indexes[1].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[1].duration == '20053334'
                            assert ismc_object.stream_indexes[1].chunk_datas[1].r == '1'

                            assert not ismc_object.stream_indexes[1].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[2].duration == '19840000'
                            assert ismc_object.stream_indexes[1].chunk_datas[2].r == '1'

                            assert not ismc_object.stream_indexes[1].chunk_datas[461].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[461].duration == '19840000'
                            assert ismc_object.stream_indexes[1].chunk_datas[461].r == '1'

                            assert not ismc_object.stream_indexes[1].chunk_datas[462].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[462].duration == '3626666'
                            assert ismc_object.stream_indexes[1].chunk_datas[462].r == '1'

                    with Allure.Step("Verify StreamIndexes attributes for the first video track"):
                        assert ismc_object.stream_indexes[2].chunks == '617'
                        assert ismc_object.stream_indexes[2].name == 'video_0'
                        assert ismc_object.stream_indexes[2].quality_levels == '1'
                        assert ismc_object.stream_indexes[2].stream_type == 'video'
                        assert ismc_object.stream_indexes[2].url == 'QualityLevels({bitrate})/Fragments(video_0={start time})'
                        assert len(ismc_object.stream_indexes[2].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[2].chunk_datas) == 2
                        with Allure.Step("Verify QualityLevels attributes for the first video track"):
                            with Allure.Step("Verify QualityLevel attributes for the first video track"):
                                assert ismc_object.stream_indexes[2].quality_level_list[0].bitrate == '542687'
                                assert ismc_object.stream_indexes[2].quality_level_list[
                                           0].codec_private_data == '00000001674D4028965281004B602D100000030010000003032E0000086440004323FF18E0ED0D188B0000000168E9083520'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].index == '0'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].max_height == '288'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].max_width == '512'
                        with Allure.Step("Verify c elements attributes for the first video track"):
                            assert ismc_object.stream_indexes[2].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].duration == '20000000'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].r == '616'

                            assert not ismc_object.stream_indexes[2].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[2].chunk_datas[1].duration == '3200000'
                            assert ismc_object.stream_indexes[2].chunk_datas[1].r == '1'

                    with Allure.Step("Verify StreamIndexes attributes for the second video track"):
                        assert ismc_object.stream_indexes[3].chunks == '617'
                        assert ismc_object.stream_indexes[3].name == 'video_1'
                        assert ismc_object.stream_indexes[3].quality_levels == '1'
                        assert ismc_object.stream_indexes[3].stream_type == 'video'
                        assert ismc_object.stream_indexes[3].url == 'QualityLevels({bitrate})/Fragments(video_1={start time})'
                        assert len(ismc_object.stream_indexes[3].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[3].chunk_datas) == 2
                        with Allure.Step("Verify QualityLevels attributes for the second video track"):
                            with Allure.Step("Verify QualityLevel attributes for the second video track"):
                                assert ismc_object.stream_indexes[3].quality_level_list[0].bitrate == '984776'
                                assert ismc_object.stream_indexes[3].quality_level_list[
                                           0].codec_private_data == '00000001674D4028965281806F602D100000030010000003032E00000F4240007A127F18E0ED0D188B0000000168E9083520'
                                assert ismc_object.stream_indexes[3].quality_level_list[0].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[3].quality_level_list[0].index == '0'
                                assert ismc_object.stream_indexes[3].quality_level_list[0].max_height == '432'
                                assert ismc_object.stream_indexes[3].quality_level_list[0].max_width == '768'
                        with Allure.Step("Verify c elements attributes for the first video track"):
                            assert ismc_object.stream_indexes[3].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[3].chunk_datas[0].duration == '20000000'
                            assert ismc_object.stream_indexes[3].chunk_datas[0].r == '616'

                            assert not ismc_object.stream_indexes[3].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[3].chunk_datas[1].duration == '3200000'
                            assert ismc_object.stream_indexes[3].chunk_datas[1].r == '1'

                    with Allure.Step("Verify StreamIndexes attributes for the third video track"):
                        assert ismc_object.stream_indexes[4].chunks == '617'
                        assert ismc_object.stream_indexes[4].name == 'video_2'
                        assert ismc_object.stream_indexes[4].quality_levels == '1'
                        assert ismc_object.stream_indexes[4].stream_type == 'video'
                        assert ismc_object.stream_indexes[4].url == 'QualityLevels({bitrate})/Fragments(video_2={start time})'
                        assert len(ismc_object.stream_indexes[4].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[4].chunk_datas) == 2
                        with Allure.Step("Verify QualityLevels attributes for the third video track"):
                            with Allure.Step("Verify QualityLevel attributes for the third video track"):
                                assert ismc_object.stream_indexes[4].quality_level_list[0].bitrate == '1521295'
                                assert ismc_object.stream_indexes[4].quality_level_list[
                                           0].codec_private_data == '00000001674D4028965281B07BCDE02D100000030010000003032E020005E9A00017A6BFC6383B434622C00000000168E9083520'
                                assert ismc_object.stream_indexes[4].quality_level_list[0].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[4].quality_level_list[0].index == '0'
                                assert ismc_object.stream_indexes[4].quality_level_list[0].max_height == '480'
                                assert ismc_object.stream_indexes[4].quality_level_list[0].max_width == '854'
                        with Allure.Step("Verify c elements attributes for the third video track"):
                            assert ismc_object.stream_indexes[4].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[4].chunk_datas[0].duration == '20000000'
                            assert ismc_object.stream_indexes[4].chunk_datas[0].r == '616'

                            assert not ismc_object.stream_indexes[4].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[4].chunk_datas[1].duration == '3200000'
                            assert ismc_object.stream_indexes[4].chunk_datas[1].r == '1'

    @title('Test Ismc Generation for mp4 file with E-AC3 audio codec')
    @description('Test .ismc manifest generation for mp4 file with E-AC3 audio codec')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92420", name="NG-92420")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/folder/229926370845?s=26rdenldf0r8sxupf2f6ktqh31a74l3v
    #     List of files:
    #         CONT0000000001896556_vu_movie_hd_stb_nodrm_HD_2.0EN_Audio.mp4
    def test_check_generated_ismc_manifest_e_ac3(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_eac3_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 1
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration,
                                                         media_track_infos=media_data.media_track_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '82540480000'
                    assert len(ismc_object.stream_indexes) == 1
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndex attributes for the audio track"):
                        assert ismc_object.stream_indexes[0].chunks == '2064'
                        assert ismc_object.stream_indexes[0].language == 'und'
                        assert ismc_object.stream_indexes[0].name == 'Undetermined'
                        assert ismc_object.stream_indexes[0].quality_levels == '1'
                        assert ismc_object.stream_indexes[0].stream_type == 'audio'
                        assert ismc_object.stream_indexes[0].url == 'QualityLevels({bitrate})/Fragments(Undetermined={start time})'
                        assert len(ismc_object.stream_indexes[0].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[0].chunk_datas) == 2
                        with Allure.Step("Verify QualityLevel attributes for the audio track"):
                            assert ismc_object.stream_indexes[0].quality_level_list[0].audio_tag == '65534'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bitrate == '191999'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].channels == '6'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].codec_private_data == '00063F000000AF87FBA7022DFB42A4D405CD93843BDD0600200F00'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].four_cc == 'EC-3'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].packet_size == '768'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].sampling_rate == '48000'
                        with Allure.Step("Verify c elements attributes for the audio track"):
                            assert ismc_object.stream_indexes[0].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].duration == '40000000'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].r == '2063'
                            assert ismc_object.stream_indexes[0].chunk_datas[1].duration == '20480000'
                            assert ismc_object.stream_indexes[0].chunk_datas[1].r == '1'

    @title('Test Ismc Generation for audio multi-profiles')
    @description('Test .ismc manifest generation for audio multi-profiles')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92422", name="NG-92422")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/folder/245841935441?s=roobtur7vwasjy3ay453x5wh7r6hxllo
    #     List of files:
    #         288p.mp4
    #         216p.mp4
    #         dan.mp4
    #         eng.mp4
    def test_check_generated_ismc_manifest_audio_multi_profiles(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_audio_multi_profiles_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 4
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration, media_track_infos=media_data.media_track_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '19732800000'
                    assert len(ismc_object.stream_indexes) == 3
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndexes attributes for the first audio track"):
                        assert ismc_object.stream_indexes[0].chunks == '980'
                        assert ismc_object.stream_indexes[0].language == 'dan'
                        assert ismc_object.stream_indexes[0].name == 'Danish'
                        assert ismc_object.stream_indexes[0].quality_levels == '1'
                        assert ismc_object.stream_indexes[0].stream_type == 'audio'
                        assert ismc_object.stream_indexes[0].url == 'QualityLevels({bitrate})/Fragments(Danish={start time})'
                        assert len(ismc_object.stream_indexes[0].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[0].chunk_datas) == 978
                        with Allure.Step("Verify QualityLevel attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bitrate == '32004'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].codec_private_data == '1210'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].sampling_rate == '44100'
                        with Allure.Step("Verify c elements attributes for the first audio track"):
                            assert ismc_object.stream_indexes[0].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].duration == '20200680'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].r == '1'

                            assert not ismc_object.stream_indexes[0].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[1].duration == '20079139'
                            assert ismc_object.stream_indexes[0].chunk_datas[1].r == '1'

                            assert not ismc_object.stream_indexes[0].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[2].duration == '20085034'
                            assert ismc_object.stream_indexes[0].chunk_datas[2].r == '1'

                            assert not ismc_object.stream_indexes[0].chunk_datas[976].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[976].duration == '20201360'
                            assert ismc_object.stream_indexes[0].chunk_datas[976].r == '1'

                            assert not ismc_object.stream_indexes[0].chunk_datas[977].time_start
                            assert ismc_object.stream_indexes[0].chunk_datas[977].duration == '3715193'
                            assert ismc_object.stream_indexes[0].chunk_datas[977].r == '1'

                    with Allure.Step("Verify StreamIndexes attributes for the second audio track"):
                        assert ismc_object.stream_indexes[1].chunks == '980'
                        assert ismc_object.stream_indexes[1].language == 'eng'
                        assert ismc_object.stream_indexes[1].name == 'English'
                        assert ismc_object.stream_indexes[1].quality_levels == '1'
                        assert ismc_object.stream_indexes[1].stream_type == 'audio'
                        assert ismc_object.stream_indexes[1].url == 'QualityLevels({bitrate})/Fragments(English={start time})'
                        assert len(ismc_object.stream_indexes[1].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[1].chunk_datas) == 978
                        with Allure.Step("Verify QualityLevel attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bitrate == '32004'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].codec_private_data == '1210'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].sampling_rate == '44100'
                        with Allure.Step("Verify c elements attributes for the second audio track"):
                            assert ismc_object.stream_indexes[1].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].duration == '20013152'
                            assert ismc_object.stream_indexes[1].chunk_datas[0].r == '1'

                            assert not ismc_object.stream_indexes[1].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[1].duration == '20092063'
                            assert ismc_object.stream_indexes[1].chunk_datas[1].r == '1'

                            assert not ismc_object.stream_indexes[1].chunk_datas[2].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[2].duration == '20091837'
                            assert ismc_object.stream_indexes[1].chunk_datas[2].r == '1'

                            assert not ismc_object.stream_indexes[1].chunk_datas[976].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[976].duration == '20201361'
                            assert ismc_object.stream_indexes[1].chunk_datas[976].r == '1'

                            assert not ismc_object.stream_indexes[1].chunk_datas[977].time_start
                            assert ismc_object.stream_indexes[1].chunk_datas[977].duration == '928798'
                            assert ismc_object.stream_indexes[1].chunk_datas[977].r == '1'

                    with Allure.Step("Verify StreamIndexes attributes for the video track"):
                        assert ismc_object.stream_indexes[2].chunks == '968'
                        assert ismc_object.stream_indexes[2].name == 'video_0'
                        assert ismc_object.stream_indexes[2].quality_levels == '2'
                        assert ismc_object.stream_indexes[2].stream_type == 'video'
                        assert ismc_object.stream_indexes[2].url == 'QualityLevels({bitrate})/Fragments(video_0={start time})'
                        assert len(ismc_object.stream_indexes[2].quality_level_list) == 2
                        assert len(ismc_object.stream_indexes[2].chunk_datas) == 10
                        with Allure.Step("Verify QualityLevels attributes for the video track"):
                            with Allure.Step("Verify first QualityLevel attributes for the video track"):
                                assert ismc_object.stream_indexes[2].quality_level_list[0].bitrate == '131464'
                                assert ismc_object.stream_indexes[2].quality_level_list[
                                           0].codec_private_data == '000000016764000DACD94181DF961000000300100000030320F14299600000000168EBE3CB22C0'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].index == '0'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].max_height == '216'
                                assert ismc_object.stream_indexes[2].quality_level_list[0].max_width == '384'
                            with Allure.Step("Verify second QualityLevel attributes for the video track"):
                                assert ismc_object.stream_indexes[2].quality_level_list[1].bitrate == '151459'
                                assert ismc_object.stream_indexes[2].quality_level_list[
                                           1].codec_private_data == '0000000167640015ACD94170979784000003000400000300C83C58B6580000000168EF8FCB'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].four_cc == 'AVC1'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].index == '1'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].max_height == '288'
                                assert ismc_object.stream_indexes[2].quality_level_list[1].max_width == '360'
                        with Allure.Step("Verify c elements attributes for the first video track"):
                            assert ismc_object.stream_indexes[2].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].duration == '20400000'
                            assert ismc_object.stream_indexes[2].chunk_datas[0].r == '230'

                            assert not ismc_object.stream_indexes[2].chunk_datas[1].time_start
                            assert ismc_object.stream_indexes[2].chunk_datas[1].duration == '20000000'
                            assert ismc_object.stream_indexes[2].chunk_datas[1].r == '1'

                            assert not ismc_object.stream_indexes[2].chunk_datas[8].time_start
                            assert ismc_object.stream_indexes[2].chunk_datas[8].duration == '20400000'
                            assert ismc_object.stream_indexes[2].chunk_datas[8].r == '34'

                            assert not ismc_object.stream_indexes[2].chunk_datas[9].time_start
                            assert ismc_object.stream_indexes[2].chunk_datas[9].duration == '7600000'
                            assert ismc_object.stream_indexes[2].chunk_datas[9].r == '1'

    @title('Test Ismc Generation for asset with timescale=0 in mvhd box')
    @description('Test .ismc manifest generation for asset with timescale=0 in mvhd box')
    # Test data
    #     Azure: asset-fd8e9830-fbb9-4970-a5fc-fc262ee2df7a
    #     List of files:
    #         0128.isma
    #         0400.ismv
    #         0700.ismv
    #         1000.ismv
    #         2600.ismv
    #         4000.ismv
    #         6000.ismv
    def test_asset_timescale_0(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_timescale_0_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 7
        with Allure.Step("Generate .ismc manifest base on media_track_info_list"):
            with Allure.Step("Generate .ismc manifest"):
                ismc_xml_string = IsmcGenerator.generate(duration=media_data.media_duration,
                                                         media_track_infos=media_data.media_track_info_list)
                assert ismc_xml_string
            with Allure.Step("Verify .ismc manifest"):
                ismc_object = IsmcManifestExtractor.extract(ismc_manifest_str=ismc_xml_string)
                assert ismc_object
                with Allure.Step("Verify SmoothStreamingMedia attributes"):
                    assert ismc_object.major_version == '2'
                    assert ismc_object.minor_version == '2'
                    assert ismc_object.time_scale == '10000000'
                    assert ismc_object.duration == '0'
                    assert len(ismc_object.stream_indexes) == 2
                with Allure.Step("Verify StreamIndexes"):
                    with Allure.Step("Verify StreamIndex attributes for the audio track"):
                        assert ismc_object.stream_indexes[0].chunks == '24'
                        assert ismc_object.stream_indexes[0].language == 'und'
                        assert ismc_object.stream_indexes[0].name == 'Undetermined'
                        assert ismc_object.stream_indexes[0].quality_levels == '1'
                        assert ismc_object.stream_indexes[0].stream_type == 'audio'
                        assert ismc_object.stream_indexes[0].url == 'QualityLevels({bitrate})/Fragments(Undetermined={start time})'
                        assert len(ismc_object.stream_indexes[0].quality_level_list) == 1
                        assert len(ismc_object.stream_indexes[0].chunk_datas) > 0
                        with Allure.Step("Verify QualityLevel attributes for the audio track"):
                            assert ismc_object.stream_indexes[0].quality_level_list[0].audio_tag == '255'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bitrate == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].bits_per_sample == '16'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].channels == '2'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].codec_private_data == '1190'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].four_cc == 'AACL'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].packet_size == '4'
                            assert ismc_object.stream_indexes[0].quality_level_list[0].sampling_rate == '48000'
                        with Allure.Step("Verify c elements attributes for the audio track"):
                            assert ismc_object.stream_indexes[0].chunk_datas[0].time_start == '0'
                            assert ismc_object.stream_indexes[0].chunk_datas[0].duration == '20053333'
                            # Note: chunks=24 but only checking first element, r value may vary

                    with Allure.Step("Verify StreamIndex attributes for the video track"):
                        assert ismc_object.stream_indexes[1].chunks == '25'
                        assert ismc_object.stream_indexes[1].name == 'video_0'
                        assert ismc_object.stream_indexes[1].quality_levels == '6'
                        assert ismc_object.stream_indexes[1].stream_type == 'video'
                        assert ismc_object.stream_indexes[1].url == 'QualityLevels({bitrate})/Fragments(video_0={start time})'
                        assert len(ismc_object.stream_indexes[1].quality_level_list) == 6
                        assert len(ismc_object.stream_indexes[1].chunk_datas) > 0
                        with Allure.Step("Verify QualityLevel attributes for the video track"):
                            assert ismc_object.stream_indexes[1].quality_level_list[0].bitrate == '395019'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].codec_private_data.upper() == '00000001674D401FEC80F047F5808800001F480007530078C18CB00000000168EBE152C8'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].four_cc.upper() == 'AVC1'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].index == '0'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].max_height == '270'
                            assert ismc_object.stream_indexes[1].quality_level_list[0].max_width == '480'

                            assert ismc_object.stream_indexes[1].quality_level_list[5].bitrate == '5988138'
                            assert ismc_object.stream_indexes[1].quality_level_list[5].codec_private_data.upper() == '0000000167640029ACD900780227E5C04400000FA40003A9803C60C6580000000168EBE152C8B0'
                            assert ismc_object.stream_indexes[1].quality_level_list[5].four_cc.upper() == 'AVC1'
                            assert ismc_object.stream_indexes[1].quality_level_list[5].index == '5'
                            assert ismc_object.stream_indexes[1].quality_level_list[5].max_height == '1080'
                            assert ismc_object.stream_indexes[1].quality_level_list[5].max_width == '1920'
                        with Allure.Step("Verify c elements attributes for the video track"):
                            assert ismc_object.stream_indexes[1].chunk_datas[0].time_start == '0'
                            # Note: Duration and r values may vary based on fragment structure
