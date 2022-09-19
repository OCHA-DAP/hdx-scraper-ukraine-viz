import logging
from os.path import join

from hdx.location.adminlevel import AdminLevel
from hdx.location.country import Country
from hdx.scraper.outputs.update_tabs import (
    get_toplevel_rows,
    update_national,
    update_sources,
    update_subnational,
    update_toplevel,
)
from hdx.scraper.runner import Runner
from hdx.scraper.utilities.fallbacks import Fallbacks
from hdx.utilities.dateparse import parse_date

from .acled import ACLED
from .fts import FTS
from .idps import IDPs
from .unhcr import UNHCR

logger = logging.getLogger(__name__)


def get_indicators(
    configuration,
    today,
    outputs,
    tabs,
    scrapers_to_run=None,
    nofilecopy=False,
    countries_override=None,
    errors_on_exit=None,
    use_live=True,
    fallbacks_root="",
):
    Country.countriesdata(
        use_live=use_live,
        country_name_overrides=configuration["country_name_overrides"],
        country_name_mappings=configuration["country_name_mappings"],
    )

    if countries_override:
        primary_countries = countries_override
    else:
        primary_countries = configuration["primary_countries"]
    configuration["countries_fuzzy_try"] = primary_countries
    adminlevel = AdminLevel(configuration)
    if fallbacks_root is not None:
        fallbacks_path = join(fallbacks_root, configuration["json"]["output"])
        levels_mapping = {
            "regional": "regional_data",
            "national": "national_data",
            "subnational": "subnational_data",
        }
        Fallbacks.add(
            fallbacks_path,
            levels_mapping=levels_mapping,
            sources_key="sources_data",
        )
    runner = Runner(
        primary_countries,
        today,
        errors_on_exit=errors_on_exit,
        scrapers_to_run=scrapers_to_run,
    )
    start_date = parse_date(configuration["additional_sources"][0]["source_date"])
    if nofilecopy:
        prioritise_scrapers = list()
    else:
        prioritise_scrapers = runner.add_resource_downloaders(
            configuration["downloadresources"]
        )
    configurable_scrapers = dict()
    for level in ("national", "subnational"):
        suffix = f"_{level}"
        configurable_scrapers[level] = runner.add_configurables(
            configuration[f"primary{suffix}"],
            level,
            adminlevel=adminlevel,
            suffix=suffix,
        )
    fts = FTS(configuration["fts"], today, primary_countries)
    unhcr = UNHCR(configuration["unhcr"], today, outputs, primary_countries)
    idps = IDPs(configuration["idps"], outputs)
    acled = ACLED(configuration["acled"], start_date, today, outputs, adminlevel)
    runner.add_customs(
        (
            fts,
            unhcr,
            idps,
            acled,
        )
    )
    runner.add_timeseries_scrapers(configuration["timeseries"], outputs)
    prioritise_scrapers.extend(
        [
            "population_national",
            "population_subnational",
            "population_regional",
        ]
    )
    runner.run(prioritise_scrapers=prioritise_scrapers)

    if "regional" in tabs:
        rows = get_toplevel_rows(runner, toplevel="regional")
        update_toplevel(outputs, rows, tab="regional")
    if "national" in tabs:
        national_names = configurable_scrapers["national"]
        national_names.insert(1, "idps")
        national_names.insert(1, "unhcr")
        national_names.insert(len(national_names) - 1, "fts")
        update_national(
            runner,
            primary_countries,
            outputs,
            names=national_names,
        )
    if "subnational" in tabs:
        update_subnational(runner, adminlevel, outputs)

    adminlevel.output_matches()
    adminlevel.output_ignored()
    adminlevel.output_errors()

    secondary_countries = configuration["secondary_countries"]
    configuration["countries_fuzzy_try"] = secondary_countries

    secondary_runner = Runner(
        secondary_countries,
        today,
        errors_on_exit=errors_on_exit,
        scrapers_to_run=scrapers_to_run,
    )
    level = "national"
    suffix = f"_{level}"
    configurable_scrapers = secondary_runner.add_configurables(
        configuration[f"secondary{suffix}"], level, suffix=suffix
    )
    secondary_runner.run()

    if "secondary_national" in tabs:
        update_national(
            secondary_runner,
            secondary_countries,
            outputs,
            names=configurable_scrapers,
            tab="secondary_national",
        )

    if "sources" in tabs:
        update_sources(
            runner,
            outputs,
            additional_sources=configuration["additional_sources"],
            secondary_runner=secondary_runner,
        )
