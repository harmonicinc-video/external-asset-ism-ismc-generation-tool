# ISM/ISMC manifests generation

harmonic_external_asset_ism_ismc_generation_tool is a command line tool to generate the ISM/ISMC manifest for the .mp4 files stored in Azure containers.
The tool parses .mp4 files from an Azure container, generates .ism and .ismc manifests if they do not exist, and loads them into the Azure container. 

## Prerequisites
- Python 3.10
- Python libs:
  - azure-core==1.29.4
  - azure-storage-blob==12.8.1
  - azure-identity==1.14.1
  - construct=2.8.8
  - pycountry==22.3.5
  - webvtt-py==0.5.1
  - ttconv==1.1.0

## Supported codecs
### Video codecs
- AVC
- HEVC
### Audio codecs
- AAC-LC
- AAC-HE (when it's compatible with AAC-LC and we interpret it as AAC-LC)
- E-AC3

## Supported formats:
# media formats:
- .mp4
- .mpi
- .ismv
- .isma
- .cmft

# text formats
- .ttml
- .vtt

## HowTo run
### With Azure Storage
```
python3 main.py -connection_string=<Azure storage account's connection string> -container_name=<Azure container name>
```
or
```
python3 main.py
```
in case if the configuration file azure_config.json has been filled (the configuration file shall be situated in the same folder as the main.py file).

### With Local Directory
```
python3 main.py -local_directory=/path/to/directory/with/mp4/files
```
This mode processes MP4 files from a local directory and generates ISM/ISMC manifests in the same directory. This option is completely independent of Azure and does not require any Azure configuration.
### azure_config.json
azure_config.json - configuration file may contain the following fields: connection_string, account_name, account_key, container_name:
```
{
  "connection_string": "DefaultEndpointsProtocol=https;AccountName=flametestextassetstorage;AccountKey=<key>;EndpointSuffix=core.windows.net",
  "account_name": "flametestextassetstorage",
  "account_key": "<key>",
  "container_name": "test2"
}
```
**Note:** The `local_directory` option is only available as a command-line argument (`-local_directory`) and cannot be configured in the azure_config.json file.
It's possible to set the `connection_string`  fileld or `account_name` and `account_key` .
If only the `account_name` and `account_key` fields are specified, the connection string is formed from them.
If all fields are set, only the `connection_string` field value is used. In this case the `account_name` and `account_key` fields are ignored.

Azure connection string can be found in Azure Portal → Storage container → Access keys → Connection string

## HowTo run with multithreading
```
python3 main.py -is_multithreading
```
or with local directory:
```
python3 main.py -local_directory=/path/to/directory -is_multithreading
```
Currently ISM/ISMC generation tool supports two modes: one-threaded and multi-threaded. Multi-threaded mode uses the maximum amount of threads your system can handle.
