import logging
from os.path import join
from shutil import move

from hdx.data.dataset import Dataset

logger = logging.getLogger(__name__)


def get_geojson(configuration, folder=""):
    dataset = Dataset.read_from_hdx(configuration["geojson"]["dataset"])
    for resource in dataset.get_resources():
        if resource.get_file_type() == "geojson":
            url, path = resource.download()
            logger.info(f"Downloading {url} to {path}")
            move(path, join(folder, "UKR_Border_Crossings.geojson"))
            break
