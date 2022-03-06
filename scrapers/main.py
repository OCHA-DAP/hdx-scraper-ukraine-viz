import logging

from hdx.location.adminone import AdminOne
from hdx.location.country import Country
from hdx.scraper.runner import Runner
from scrapers.utilities.update_tabs import (
    update_national, update_sources,
)
#from .fts import FTS
#from .unhcr import UNHCR

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
    for level in "national", :  # "subnational", "regional":
        suffix = f"_{level}"
        configurable_scrapers[level] = runner.add_configurables(
            configuration[f"scraper{suffix}"], level, suffix=suffix
        )
#    fts = FTS(configuration["fts"], today, countries, basic_auths)
#    unhcr = UNHCR(configuration["unhcr"], today, countries, downloader)
#     runner.add_customs(
#         (
#             fts,
#             unhcr,
#         )
#     )
    runner.run(
        prioritise_scrapers=(
            "population_national",
            "population_subnational",
            "population_regional",
        )
    )

    # global_rows = get_global_rows(
    #     runner, global_names, {"who_covid": {"gho": "global"}}
    # )
    # regional_rows = get_regional_rows(runner, RegionLookups.regions + ["global"])
    # if "world" in tabs:
    #     update_world(
    #         outputs, global_rows, regional_rows, configuration["regional"]["global"]
    #     )
    # if "regional" in tabs:
    #     additional_global_headers = (
    #         "Cumulative_cases",
    #         "Cumulative_deaths",
    #         "RequiredHRPFunding",
    #         "HRPFunding",
    #         "HRPPercentFunded",
    #     )
    #     update_regional(
    #         outputs,
    #         regional_rows,
    #         global_rows,
    #         additional_global_headers,
    #     )
    if "national" in tabs:
        update_national(
            runner,
            countries,
            outputs,
        )
    # if "subnational" in tabs:
    #     update_subnational(runner, subnational_names, adminone, outputs)

    adminone.output_matches()
    adminone.output_ignored()
    adminone.output_errors()

    if "sources" in tabs:
        update_sources(runner, outputs)
    return countries
