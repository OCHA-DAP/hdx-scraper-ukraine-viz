import logging

from hdx.location.adminone import AdminOne
from hdx.location.country import Country
from hdx.scraper.runner import Runner
from scrapers.utilities.update_tabs import (
    update_national,
    update_regional,
    update_sources, update_subnational,
)

from .fts import FTS
# from .unhcr import UNHCR
from .unhcr import UNHCR

logger = logging.getLogger(__name__)


def get_indicators(
    configuration,
    today,
    retriever,
    outputs,
    tabs,
    scrapers_to_run=None,
    basic_auths=dict(),
    other_auths=dict(),
    countries_override=None,
    errors_on_exit=None,
    use_live=True,
):
    Country.countriesdata(
        use_live=use_live,
        country_name_overrides=configuration["country_name_overrides"],
        country_name_mappings=configuration["country_name_mappings"],
    )

    if countries_override:
        countries = countries_override
    else:
        countries = configuration["countries"]
    configuration["countries_fuzzy_try"] = countries
    downloader = retriever.downloader
    adminone = AdminOne(configuration)
    runner = Runner(
        countries,
        adminone,
        downloader,
        basic_auths,
        today,
        errors_on_exit=errors_on_exit,
        scrapers_to_run=scrapers_to_run,
    )
    configurable_scrapers = dict()
    for level in ("national", "subnational"):
        suffix = f"_{level}"
        configurable_scrapers[level] = runner.add_configurables(
            configuration[f"scraper{suffix}"], level, suffix=suffix
        )
    fts = FTS(configuration["fts"], today, countries, basic_auths)
    unhcr = UNHCR(configuration["unhcr"], today, outputs, downloader)
    runner.add_customs(
        (
            fts,
            unhcr,
        )
    )
    runner.run(
        prioritise_scrapers=(
            "population_national",
            "population_subnational",
            "population_regional",
        )
    )

    national_names = configurable_scrapers["national"]
    national_names.insert(1, "unhcr")
    national_names.insert(len(national_names) - 1, "fts")
    if "regional" in tabs:
        update_regional(runner, outputs)
    if "national" in tabs:
        update_national(
            runner,
            national_names,
            countries,
            outputs,
        )
    if "subnational" in tabs:
        update_subnational(runner, adminone, outputs)

    adminone.output_matches()
    adminone.output_ignored()
    adminone.output_errors()

    if "sources" in tabs:
        update_sources(runner, outputs)
    return countries
