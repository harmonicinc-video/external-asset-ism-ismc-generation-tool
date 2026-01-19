from typing import List

from allure_commons._allure import title, description, issue, link

from external_asset_ism_ismc_generation_tool.media_data_parser.media_data_parser import MediaDataParser
from external_asset_ism_ismc_generation_tool.media_data_parser.model.media_data import MediaData
from external_asset_ism_ismc_generation_tool.mss_server_manifest import IsmGenerator
from external_asset_ism_ismc_generation_tool.text_data_parser.model.text_data_info import TextDataInfo
from tests.test_utils.common.allure_helper import Allure
from tests.test_utils.common.common import Common
from tests.test_utils.ism_manifest_extractor.ism_manifest_extractor import IsmManifestExtractor


class TestIsmGeneration:

    @title('Test Ism Generation for 3 mp4 files with 2 audio tracks and 1 video track')
    @description('Test .ism manifest generation for 3 mp4 files with 2 audio tracks and 1 video track')
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223784358854
    #     List of files:
    #         Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ1.2.0DE2.0EN.16x9.mp4
    #         Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ3.2.0DE2.0EN.16x9.mp4
    #         Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ5.2.0DE2.0EN.16x9.mp4
    def test_check_generated_ism_manifest_3_mp4(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_avc_aacle_2_audios_3_videos_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 5
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 2
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 3
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == 'Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify audios"):
                        audios = ism_object.body.audios
                        assert len(audios) == 2

                        assert audios[0].src == 'Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ1.2.0DE2.0EN.16x9.mp4'
                        assert audios[0].system_bitrate == "64000"
                        assert audios[0].system_language == "deu"
                        assert audios[0].params[0].name == "trackID"
                        assert audios[0].params[0].value == "2"
                        assert audios[0].params[0].value_type == "data"

                        assert audios[1].src == 'Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ1.2.0DE2.0EN.16x9.mp4'
                        assert audios[1].system_bitrate == "64000"
                        assert audios[1].system_language == "eng"
                        assert audios[1].params[0].name == "trackID"
                        assert audios[1].params[0].value == "3"
                        assert audios[1].params[0].value_type == "data"
                    with Allure.Step("Verify videos"):
                        videos = ism_object.body.videos
                        assert len(videos) == 3

                        assert videos[0].src == 'Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ1.2.0DE2.0EN.16x9.mp4'
                        assert videos[0].system_bitrate == "99966"
                        assert videos[0].params[0].name == "trackID"
                        assert videos[0].params[0].value == "1"
                        assert videos[0].params[0].value_type == "data"

                        assert videos[1].src == 'Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ3.2.0DE2.0EN.16x9.mp4'
                        assert videos[1].system_bitrate == "299963"
                        assert videos[1].params[0].name == "trackID"
                        assert videos[1].params[0].value == "1"
                        assert videos[1].params[0].value_type == "data"

                        assert videos[2].src == 'Tell_It_Like_a_Woman_-_VU_GAS_CC_-_HD_-_DE_CWO-5579435.VU.CC.OTT.VQ5.2.0DE2.0EN.16x9.mp4'
                        assert videos[2].system_bitrate == "599991"
                        assert videos[2].params[0].name == "trackID"
                        assert videos[2].params[0].value == "1"
                        assert videos[2].params[0].value_type == "data"

    @title('Test Ism Generation for 2 mp4 files with 2 audio tracks and 1 video track')
    @description('Test .ism manifest generation for 2 mp4 files with 2 audio tracks and 1 video track')
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223787106023
    #     List of files:
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ4.mp4
    def test_check_generated_ism_manifest_2_mp4(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_hevc_aacle_2_audios_2_videos_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 4
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 2
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 2
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == 'Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify audios"):
                        audios = ism_object.body.audios
                        assert len(audios) == 2

                        assert audios[0].src == 'Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.mp4'
                        assert audios[0].system_bitrate == "160000"
                        assert audios[0].system_language == "deu"
                        assert audios[0].params[0].name == "trackID"
                        assert audios[0].params[0].value == "2"
                        assert audios[0].params[0].value_type == "data"

                        assert audios[1].src == 'Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.mp4'
                        assert audios[1].system_bitrate == "160000"
                        assert audios[1].system_language == "eng"
                        assert audios[1].params[0].name == "trackID"
                        assert audios[1].params[0].value == "3"
                        assert audios[1].params[0].value_type == "data"
                    with Allure.Step("Verify videos"):
                        videos = ism_object.body.videos
                        assert len(videos) == 2

                        assert videos[0].src == 'Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.mp4'
                        assert videos[0].system_bitrate == "1700474"
                        assert videos[0].params[0].name == "trackID"
                        assert videos[0].params[0].value == "1"
                        assert videos[0].params[0].value_type == "data"

                        assert videos[1].src == 'Terrifier2_4K_CP-830377_4K_Dual_648535_VQ4.mp4'
                        assert videos[1].system_bitrate == "5000329"
                        assert videos[1].params[0].name == "trackID"
                        assert videos[1].params[0].value == "1"
                        assert videos[1].params[0].value_type == "data"

    @title('Test Ism Generation for 2 mp4 files and 1 vtt file')
    @description('Test .ism manifest generation for 2 mp4 files and 1 vtt file')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92425", name="NG-92425")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223787106023
    #     List of files:
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ4.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ4.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_PROXY_648535_subtitle.vtt
    def test_check_generated_ism_manifest_2_mp4_vtt(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_vtt_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 8
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 6
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 2
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Get text stream tracks info"):
                text_datas: List[TextDataInfo] = Common.get_test_data_from_json(Common.get_data_file_path('test_vtt_data.json'))['text_data_infos_list']
                text_streams = IsmGenerator.get_text_streams(media_track_infos=media_data.media_track_info_list, text_datas=text_datas)
                assert text_streams
                assert len(text_streams) == 1
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos, text_streams=text_streams)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == 'Terrifier2_4K_CP-830377_4K_Dual_648535_VQ4.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify text streams"):
                        text_streams = ism_object.body.text_streams
                        assert len(text_streams) == 1

                        assert text_streams[0].src == 'Terrifier2_4K_CP-830377_4K_Dual_PROXY_648535_subtitle.vtt'
                        assert text_streams[0].system_bitrate == "138"
                        assert text_streams[0].params[0].name == "trackID"
                        assert text_streams[0].params[0].value == "6"
                        assert text_streams[0].params[0].value_type == "data"

    @title('Test Ism Generation for mp4 and ttml file')
    @description('Test .ism manifest generation for mp4 and ttml file')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92426", name="NG-92426")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/s/yj2ydlepvbgdbhejy7spkcku57xfxcu9/folder/223787106023
    #     List of files:
    #         Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.mp4
    #         Terrifier2_4K_CP-830377_4K_Dual_PROXY_648535_subtitle.ttml
    def test_check_generated_ism_manifest_mp4_ttml(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_ttml_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 3
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 2
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 1
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Get text stream tracks info"):
                text_datas: List[TextDataInfo] = Common.get_test_data_from_json(Common.get_data_file_path('test_ttml_data.json'))['text_data_infos_list']
                text_streams = IsmGenerator.get_text_streams(media_track_infos=media_data.media_track_info_list, text_datas=text_datas)
                assert text_streams
                assert len(text_streams) == 1
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos, text_streams=text_streams)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == 'Terrifier2_4K_CP-830377_4K_Dual_648535_VQ2.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify text streams"):
                        text_streams = ism_object.body.text_streams
                        assert len(text_streams) == 1

                        assert text_streams[0].src == 'Terrifier2_4K_CP-830377_4K_Dual_PROXY_648535_subtitle.ttml'
                        assert text_streams[0].system_bitrate == "292"
                        assert text_streams[0].params[0].name == "trackID"
                        assert text_streams[0].params[0].value == "4"
                        assert text_streams[0].params[0].value_type == "data"

    @title('Test Ism Generation for mp4, mpi and cmft files')
    @description('Test .ism manifest generation for mp4, mpi and cmft files')
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
    def test_check_generated_ism_manifest_mp4_mpi_cmft(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_mpi_cmft_data.json'))['media_datas']
                assert mp4_datas
                mp4_media_index_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_mpi_cmft_data.json'))['media_index_datas']
                assert mp4_media_index_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas, mp4_media_index_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 4
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 1
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 2
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Get text stream tracks info"):
                text_streams = IsmGenerator.get_text_streams(media_track_infos=media_data.media_track_info_list, text_datas=[])
                assert text_streams
                assert len(text_streams) == 1
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos, text_streams=text_streams)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == '302be42116754716ab8ccbc37a5fd68fAR.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify audio streams"):
                        audio_streams = ism_object.body.audios
                        assert len(audio_streams) == 1
                        assert audio_streams[0].src == '302be42116754716ab8ccbc37a5fd68f_256x144_150.mp4'
                        assert audio_streams[0].system_bitrate == "128076"
                        assert audio_streams[0].system_language == "und"
                        assert len(audio_streams[0].params) == 3
                        assert audio_streams[0].params[0].name == "trackID"
                        assert audio_streams[0].params[0].value == "2"
                        assert audio_streams[0].params[0].value_type == "data"
                        assert audio_streams[0].params[1].name == "trackName"
                        assert audio_streams[0].params[1].value == "Undetermined"
                        assert audio_streams[0].params[1].value_type == "data"
                        assert audio_streams[0].params[2].name == "trackIndex"
                        assert audio_streams[0].params[2].value == "302be42116754716ab8ccbc37a5fd68f_256x144_150_2.mpi"
                        assert audio_streams[0].params[2].value_type == "data"
                    with Allure.Step("Verify video streams"):
                        video_streams = ism_object.body.videos
                        assert len(video_streams) == 2
                        assert video_streams[0].src == '302be42116754716ab8ccbc37a5fd68f_256x144_150.mp4'
                        assert video_streams[0].system_bitrate == "153691"
                        assert len(video_streams[0].params) == 2
                        assert video_streams[0].params[0].name == "trackID"
                        assert video_streams[0].params[0].value == "1"
                        assert video_streams[0].params[0].value_type == "data"
                        assert video_streams[0].params[1].name == "trackIndex"
                        assert video_streams[0].params[1].value == "302be42116754716ab8ccbc37a5fd68f_256x144_150_1.mpi"
                        assert video_streams[0].params[1].value_type == "data"

                        assert video_streams[1].src == '302be42116754716ab8ccbc37a5fd68f_384x216_250.mp4'
                        assert video_streams[1].system_bitrate == "255149"
                        assert len(video_streams[1].params) == 2
                        assert video_streams[1].params[0].name == "trackID"
                        assert video_streams[1].params[0].value == "1"
                        assert video_streams[1].params[0].value_type == "data"
                        assert video_streams[1].params[1].name == "trackIndex"
                        assert video_streams[1].params[1].value == "302be42116754716ab8ccbc37a5fd68f_384x216_250_1.mpi"
                        assert video_streams[1].params[1].value_type == "data"
                    with Allure.Step("Verify text streams"):
                        text_streams = ism_object.body.text_streams
                        assert len(text_streams) == 1
                        assert text_streams[0].src == '302be42116754716ab8ccbc37a5fd68fAR.cmft'
                        assert text_streams[0].system_bitrate == "1595"
                        assert text_streams[0].params[0].name == "trackID"
                        assert text_streams[0].params[0].value == "1"
                        assert text_streams[0].params[0].value_type == "data"

    @title('Test Ism Generation for 3 ismv and 2 isma files with multiple moof boxes')
    @description('Test .ism manifest generation for 3 ismv and 2 isma files with multiple moof boxes')
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
    def test_check_generated_ism_manifest_ismv_isma(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_isma_ismv_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 5
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 2
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 3
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == '0530487-BROOKLYN_NINE_NIN_E013-HD-FI_1000.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify audios"):
                        audios = ism_object.body.audios
                        assert len(audios) == 2

                        assert audios[0].src == '0530487-BROOKLYN_NINE_NIN_E013-HD-FI_128_fra.isma'
                        assert audios[0].system_bitrate == "1536000"
                        assert audios[0].system_language == "fra"
                        assert audios[0].params[0].name == "trackID"
                        assert audios[0].params[0].value == "8"
                        assert audios[0].params[0].value_type == "data"
                        assert audios[0].params[1].name == "trackName"
                        assert audios[0].params[1].value == "French"
                        assert audios[0].params[1].value_type == "data"

                        assert audios[1].src == '0530487-BROOKLYN_NINE_NIN_E013-HD-FI_128_eng.isma'
                        assert audios[1].system_bitrate == "1536000"
                        assert audios[1].system_language == "eng"
                        assert audios[1].params[0].name == "trackID"
                        assert audios[1].params[0].value == "9"
                        assert audios[1].params[0].value_type == "data"
                        assert audios[1].params[1].name == "trackName"
                        assert audios[1].params[1].value == "English"
                        assert audios[1].params[1].value_type == "data"

                    with Allure.Step("Verify videos"):
                        videos = ism_object.body.videos
                        assert len(videos) == 3

                        assert videos[0].src == '0530487-BROOKLYN_NINE_NIN_E013-HD-FI_550.ismv'
                        assert videos[0].system_bitrate == "542687"
                        assert videos[0].params[0].name == "trackID"
                        assert videos[0].params[0].value == "1"
                        assert videos[0].params[0].value_type == "data"

                        assert videos[1].src == '0530487-BROOKLYN_NINE_NIN_E013-HD-FI_1000.ismv'
                        assert videos[1].system_bitrate == "984776"
                        assert videos[1].params[0].name == "trackID"
                        assert videos[1].params[0].value == "2"
                        assert videos[1].params[0].value_type == "data"

                        assert videos[2].src == '0530487-BROOKLYN_NINE_NIN_E013-HD-FI_1550.ismv'
                        assert videos[2].system_bitrate == "1521295"
                        assert videos[2].params[0].name == "trackID"
                        assert videos[2].params[0].value == "3"
                        assert videos[2].params[0].value_type == "data"

    @title('Test Ism Generation for mp4 file with E-AC3 audio codec')
    @description('Test .ism manifest generation for mp4 file with E-AC3 audio codec')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92420", name="NG-92420")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/folder/229926370845?s=26rdenldf0r8sxupf2f6ktqh31a74l3v
    #     List of files:
    #         CONT0000000001896556_vu_movie_hd_stb_nodrm_HD_2.0EN_Audio.mp4
    def test_check_generated_ism_manifest_mp4_e_ac3(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_eac3_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 1
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 1
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".mp4")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == 'CONT0000000001896556_vu_movie_hd_stb_nodrm_HD_2.0EN_Audio.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify audio streams"):
                        audio_streams = ism_object.body.audios
                        assert len(audio_streams) == 1
                        assert len(audio_streams[0].params) == 2

                        assert audio_streams[0].src == 'CONT0000000001896556_vu_movie_hd_stb_nodrm_HD_2.0EN_Audio.mp4'
                        assert audio_streams[0].system_bitrate == "191999"
                        assert audio_streams[0].system_language == "und"
                        assert audio_streams[0].params[0].name == "trackID"
                        assert audio_streams[0].params[0].value == "2"
                        assert audio_streams[0].params[0].value_type == "data"
                        assert audio_streams[0].params[1].name == "trackName"
                        assert audio_streams[0].params[1].value == "Undetermined"
                        assert audio_streams[0].params[1].value_type == "data"

    @title('Test Ism Generation for audio multi-profiles')
    @description('Test .ism manifest generation for audio multi-profiles')
    @issue(url="https://jira360.harmonicinc.com/browse/NG-92422", name="NG-92422")
    @link(url="https://confluence360.harmonicinc.com/pages/viewpage.action?pageId=484883292", name="[Test Plan] - ISM/ISMC generation tool")
    # Test data
    #     Box: https://harmonicinc.app.box.com/folder/245841935441?s=roobtur7vwasjy3ay453x5wh7r6hxllo
    #     List of files:
    #         288p.mp4
    #         216p.mp4
    #         dan.mp4
    #         eng.mp4
    def test_check_generated_ism_manifest_audio_multi_profiles(self):
        with Allure.Step("Prepare test data"):
            with Allure.Step("Get data from file"):
                mp4_datas = Common.get_test_data_from_json(Common.get_data_file_path('test_audio_multi_profiles_data.json'))['media_datas']
                assert mp4_datas
            with Allure.Step("Get media_track_info_list from mp4_datas"):
                media_data: MediaData = MediaDataParser.get_media_data(mp4_datas)
                assert media_data.media_track_info_list
                assert len(media_data.media_track_info_list) == 4
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 2
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 2
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == '216p.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify audio streams"):
                        audio_streams = ism_object.body.audios
                        assert len(audio_streams) == 2

                        assert audio_streams[0].src == 'dan.mp4'
                        assert audio_streams[0].system_bitrate == "32004"
                        assert audio_streams[0].system_language == "dan"
                        assert len(audio_streams[0].params) == 2
                        assert audio_streams[0].params[0].name == "trackID"
                        assert audio_streams[0].params[0].value == "1"
                        assert audio_streams[0].params[0].value_type == "data"
                        assert audio_streams[0].params[1].name == "trackName"
                        assert audio_streams[0].params[1].value == "Danish"
                        assert audio_streams[0].params[1].value_type == "data"

                        assert audio_streams[1].src == 'eng.mp4'
                        assert audio_streams[1].system_bitrate == "32004"
                        assert audio_streams[1].system_language == "eng"
                        assert len(audio_streams[1].params) == 2
                        assert audio_streams[1].params[0].name == "trackID"
                        assert audio_streams[1].params[0].value == "1"
                        assert audio_streams[1].params[0].value_type == "data"
                        assert audio_streams[1].params[1].name == "trackName"
                        assert audio_streams[1].params[1].value == "English"
                        assert audio_streams[1].params[1].value_type == "data"

                    with Allure.Step("Verify video streams"):
                        video_streams = ism_object.body.videos
                        assert len(video_streams) == 2
                        assert video_streams[0].src == '216p.mp4'
                        assert video_streams[0].system_bitrate == "131464"
                        assert len(video_streams[0].params) == 1
                        assert video_streams[0].params[0].name == "trackID"
                        assert video_streams[0].params[0].value == "1"
                        assert video_streams[0].params[0].value_type == "data"

                        assert video_streams[1].src == '288p.mp4'
                        assert video_streams[1].system_bitrate == "151459"
                        assert len(video_streams[1].params) == 1
                        assert video_streams[1].params[0].name == "trackID"
                        assert video_streams[1].params[0].value == "1"
                        assert video_streams[1].params[0].value_type == "data"

    @title('Test Ism Generation for asset with timescale=0 in mvhd box')
    @description('Test .ism manifest generation for asset with timescale=0 in mvhd box')
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
        with Allure.Step("Generate .ism manifest base on media_track_info_list"):
            with Allure.Step("Get audio tracks info"):
                audios = IsmGenerator.get_audios(media_track_infos=media_data.media_track_info_list)
                assert audios
                assert len(audios) == 1
            with Allure.Step("Get video tracks info"):
                videos = IsmGenerator.get_videos(media_track_infos=media_data.media_track_info_list)
                assert videos
                assert len(videos) == 6
            with Allure.Step("Generate .ism manifest"):
                server_manifest_name = f'{list(mp4_datas.keys())[0].split(".")[0]}'
                ism_xml_string = IsmGenerator.generate(server_manifest_name, audios=audios, videos=videos)
                assert ism_xml_string
            with Allure.Step("Verify .ism manifest"):
                ism_object = IsmManifestExtractor.extract(ism_manifest_str=ism_xml_string)
                assert ism_object
                with Allure.Step("Verify ism manifest head"):
                    assert ism_object.head
                    meta_list = ism_object.head.meta_list
                    assert meta_list
                    assert len(meta_list) == 3
                    assert meta_list[0].name == 'formats'
                    assert meta_list[0].content == 'mp4'
                    assert meta_list[1].name == 'fragmentsPerHLSSegment'
                    assert meta_list[1].content == '1'
                    assert meta_list[2].name == 'clientManifestRelativePath'
                    assert meta_list[2].content == '0128.ismc'
                with Allure.Step("Verify ism manifest body"):
                    with Allure.Step("Verify audios"):
                        audios = ism_object.body.audios
                        assert len(audios) == 1

                        assert audios[0].src == '0128.isma'
                        assert audios[0].params[0].name == "trackID"
                        assert audios[0].params[0].value_type == "data"

                    with Allure.Step("Verify videos"):
                        videos = ism_object.body.videos
                        assert len(videos) == 6

                        assert videos[0].src == '0400.ismv'
                        assert videos[0].params[0].name == "trackID"
                        assert videos[0].params[0].value_type == "data"

                        assert videos[1].src == '0700.ismv'
                        assert videos[1].params[0].name == "trackID"
                        assert videos[1].params[0].value_type == "data"

                        assert videos[2].src == '1000.ismv'
                        assert videos[2].params[0].name == "trackID"
                        assert videos[2].params[0].value_type == "data"

                        assert videos[3].src == '2600.ismv'
                        assert videos[3].params[0].name == "trackID"
                        assert videos[3].params[0].value_type == "data"

                        assert videos[4].src == '4000.ismv'
                        assert videos[4].params[0].name == "trackID"
                        assert videos[4].params[0].value_type == "data"

                        assert videos[5].src == '6000.ismv'
                        assert videos[5].params[0].name == "trackID"
                        assert videos[5].params[0].value_type == "data"

