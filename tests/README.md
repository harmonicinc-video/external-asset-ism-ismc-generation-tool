# Tests for ISM/ISMC manifests generation tool

harmonic_external_asset_ism_ismc_generation_tool is a command line tool to generate the ISM/ISMC manifest for the .mp4 files stored in Azure containers.
The tool parses .mp4 files from an Azure container, generates .ism and .ismc manifests if they do not exist, and loads them into the Azure container.
tests is a module for testing external_asset_ism_ismc_generation tool.


## Prerequisites
- Python 3.12+
- Python libs:
  - azure-core==1.29.4
  - azure-storage-blob==12.8.1
  - azure-identity==1.14.1
  - construct==2.8.8
  - pycountry==23.12.7
  - allure-pytest==2.13.5 
  - allure-python-commons==2.13.5
  - pytest-xdist==2.3.0

## Test assets are encrypted, they need to be decrypted with the following command and TEST_ASSET_KEY to be replaced by the actual value
gpg --quiet --batch --yes --decrypt-files --passphrase="$TEST_ASSET_KEY" ./data/*.gpg

## HowTo run
Run from the repository root:
```
pytest [path_to_test_file[::TestClass::test_case]]
```
To run all tests:
```
pytest
```
To run all tests from test_ismc_generation.py:
```
pytest tests/integration_tests/test_ismc_generation.py
```
To run test_check_generated_ism_manifest_2_mp4 only:
```
pytest tests/integration_tests/test_ism_generation.py::TestIsmGeneration::test_check_generated_ism_manifest_2_mp4
```

## Timing and configuration regressions

```bash
python3 -m pytest tests/test_local_media_data_parser.py tests/test_media_data_parser.py tests/test_settings_and_manifest_names.py tests/test_main.py -q
```

Synthetic binary boxes and track metadata cover version 0/1 edit lists, signed
composition offsets, movie/media timescales, leading empty edits, media trims,
finite/open-ended durations, and both room02 manifest timelines without requiring
the large source MP4. Coverage also includes chunk-repeat grouping, whole-chunk
alignment trims, non-overlapping tracks, unchanged subtitles, non-mutating mode
switching, MPI start-time replacement, invalid edit metadata, worker error
propagation, JSON boolean validation, and the value-free negative CLI flags.

Existing JSON fixtures exercise full media parsing and manifest generation for
multiple codecs, renditions, index files, and subtitle formats. These tests do not
run the downstream OTT packager or validate resulting DASH/HLS playback.

## How to prepare data for tests

For preparing test data run `generate_test_data.py` script:
```bash
$ cd external_asset_ism_ismc_generation_tool
$ py generate_test_data.py -h
usage: generate_test_data.py [-h] [-connection_string connection_string] [-container_name container_name] [-is_multithreading] [-output_name output_name]
                                                                                                                                                         
Script to generate test data from files stored in Azure container.                                                                                       
                                                                                                                                                         
options:                                                                                                                                                 
  -h, --help            show this help message and exit                                                                                                  
  -connection_string connection_string                                                                                                                   
                        Connection string for the Azure Storage account.                                                                                 
  -container_name container_name                                                                                                                         
                        Azure container name
  -is_multithreading    Enable multi-threaded mode. Default is single-threaded mode.
  -output_name output_name
                        Name of the output json test data file.
```

The script connects to Azure container where the test files are located (mp4, mpi, ttml, cmft and so on).
In case the `-connection_string` and `-container_name` are ommited, the script will try to retrieve them from `azure_config.json`.
Therefore, it is necessary to make sure that the connection string and container name are specified in one of the ways.

### Usage example:
Once the script finishes its execution, the output json file will be available in `external_asset_ism_ismc_generation_tool/tests/data`.
```bash
$ generate_test_data.py -output_name my_generated_test_data
...
2024-09-27 16:53:45,966 - INFO - generate_test_data - Saving test data to tests/data/my_generated_test_data.json

$ ls -la tests/data
total 2940
drwxr-xr-x 1 username 1049089       0 Sep 27 17:04 .
drwxr-xr-x 1 username 1049089       0 Sep 27 17:04 ..
-rw-r--r-- 1 username 1049089 3005514 Sep 27 17:04 my_generated_test_data.json
```
The test data can be read from json as shown below:
```py
from tests.test_utils.common.common import Common
...

test_data = Common.get_test_data_from_json(Common.get_data_file_path('my_generated_test_data.json'))
assert test_data
media_datas = test_data["media_datas"]
media_index_datas = test_data["media_index_datas"]
text_data_infos_list = test_data["text_data_infos_list"]
assert media_datas
assert media_index_datas
assert text_data_infos_list
...
```
**Notes:** 
 - the `media_datas` is generated based on `*.mp4`, `*.ismv`, `*.isma`, `*.cmft` files stored in Azure container.
 - the `media_index_datas` is generated based on `*.mpi` files stored in Azure container.
 - the `text_data_infos_list` is generated based on `*.ttml`, `*.vtt` files stored in Azure container.

Afterward, these data can be used in the tests:
```py
...
  with Allure.Step("Get media_track_info_list from media_datas"):
    media_data: MediaData = MediaDataParser.get_media_data(media_datas)
    assert media_data.media_track_info_list
    assert len(media_data.media_track_info_list) == 5
...
```