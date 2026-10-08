from pathlib import Path
import click
from TiMBA.main import run_timba, parameter_setter
from TiMBA.data_management.Load_Data import check_and_load_data
from TiMBA.parameters.paths import (
    GIT_USER, GIT_REPO, GIT_BRANCH, DESTINATION_PATH, GIT_FOLDER
)
from TiMBA.logic.model_extensions import run_extensions
from TiMBA.parameters import INPUT_WORLD_PATH
from TiMBA.parameters.paths import OUTPUT_DIR, ADDINFOPTHTOOLBOX 
from TiMBA.parameters.Defines import ParamNames
from TiMBA.data_management.ParameterCollector import ParameterCollector
from TiMBA.user_io.default_parameters import user_input
from c_module.logic.main import C_Module
import warnings
from Toolbox.toolbox import timba_dashboard
import traceback
warnings.simplefilter(action='ignore', category=FutureWarning)


@click.group()
def cli():
    pass

@cli.command("run")
@click.option(
    '-Y', '--year', 
    default=user_input[ParamNames.year.value], 
    show_default=True, 
    required=True, 
    type=int, 
    help="Starting year."
)

@click.option(
    '-MP', '--max_period', 'max_period', 
    default=user_input[ParamNames.max_period.value], 
    show_default=True, 
    required=True, 
    type=int, 
    help="Maximum amount of periods to forecast."
)

@click.option(
    '-PP', 
    '--calc_product_price', "calc_product_price", 
    default=user_input[ParamNames.product_price.value],
    show_default=True, required=True, type=str,
    help='''Flag to compute product prices as shadow or calculated
        prices. Choose shadow_PP for shadow prices and calculated_PP for
        calculated prices. (Only shadow prices were validated
        extensively)'''
)

@click.option(
    '-WP', '--calc_world_price', "calc_world_price",
    default=user_input[ParamNames.world_price.value],
    show_default=True, 
    required=True, 
    type=str,
    help='''Flag to compute world prices as shadow, constant or
        average prices. Choose shadow_WP for shadow prices and
        constant_WP for constant prices, and average_WP for
        average prices. (Only shadow prices were validated
        extensively)'''
)

@click.option(
    '-MB', '--material_balance', "material_balance",
    default=user_input[ParamNames.material_balance.value],
    show_default=True, 
    required=True, 
    type=str,
    help='''Flag to specify the adopted material balance. Choose
        C_specific_MB for commodity specific material balance,
        RC_specific_MB for region and commodity specific material
        balance, RCG_specific_MB for region and commodity group
        specific material balance.'''
)

@click.option(
    '-GMB', '--global_material_balance', 'global_material_balance',
    default=user_input[ParamNames.global_material_balance.value],
    show_default=True, 
    required=False, 
    type=bool,
    help='''Flag to activate global material balance
        balancing all wood flows globally'''
)

@click.option(
    '-TF', '--trans_imp_exp_factor', 'transportation_impexp_factor',
    default=user_input[ParamNames.transportation_factor.value],
    show_default=True, 
    required=True, 
    type=float,
    help="Computation factor for Transportation Import/Export."
)

@click.option(
    '-S', '--serialization', 'serialization',
    default=user_input[ParamNames.serialization.value],
    show_default=True, required=False, type=bool,
    help='If true input data will be read from stored pkl files.'
)

@click.option(
    '-D', '--dynamization', 'dynamization_activated',
    default=user_input[ParamNames.dynamization_activated.value],
    show_default=True, 
    required=False, 
    type=bool,
    help='''If true dynamization of TiMBA will be activated,
        if not the model will not develop further.'''
)
@click.option(
    '-COQ', '--cleaned_opt_quantity', 'cleaned_opt_quantity',
    default=user_input[ParamNames.cleaned_opt_quantity.value], 
    show_default=True,
    required=False, 
    type=bool,
    help='Flag to clean optimization quantities after extraction'
)

@click.option(
    '-CP', '--capped_prices', 'capped_prices',
    default=user_input[ParamNames.capped_prices.value],
    show_default=True, 
    required=False, 
    type=bool,
    help='''If activated prices will be capped by a maximum.
        (Only not capped prices were validated extensively)'''
)

@click.option(
    '-VO', '--verb_opt_log', 'verbose_optimization_logger',
    default=user_input[ParamNames.verbose_optimization_logger.value],
    show_default=True, 
    required=False, 
    type=bool,
    help='If true the logs will show verbose optimization output.'
)

@click.option(
    '-VT', '--verb_calc_log', 'verbose_calculation_logger',
    default=user_input[ParamNames.verbose_calculation_logger.value],
    show_default=True,
    required=False, 
    type=bool,
    help="If true the logs will show verbose calculation informations."
)

@click.option(
    '-FP', '--folderpath', 'folderpath', 
    required=False, 
    type=click.Path(
        file_okay=False, 
        writable=True, 
        path_type=Path
    ), 
    default=Path.cwd(), 
    show_default=f"current working directory: {Path.cwd()}",
    help="Path to directory with Input/Output folder."
)

@click.option(
    '-C', '--activate_cmodule', 'activate_cmodule',
    default=False, 
    show_default=True, 
    required=False, 
    type=bool,
    help="Flag to activate carbon module."
)

@click.option(
    '-SD', '--show_dashboard', 'show_dashboard', 
    default=False, 
    show_default=True, 
    required=False, 
    type=bool,
    help="""If true the the dashboard with the results from all 
        scenarios will open automatically after simulations are done."""
)

def timba_cli(year, max_period, calc_product_price, calc_world_price, material_balance, global_material_balance,
              transportation_impexp_factor, serialization, dynamization_activated, cleaned_opt_quantity, capped_prices,
              verbose_optimization_logger, verbose_calculation_logger, folderpath, activate_cmodule,show_dashboard):
    """start TiMBA simulations"""
    
    Parameters = parameter_setter()
    Parameters.year = year
    Parameters.max_period = max_period
    Parameters.calc_product_prices = calc_product_price
    Parameters.calc_world_prices = calc_world_price
    Parameters.transportation_imp_exp_bound_factor = transportation_impexp_factor
    Parameters.material_balance = material_balance
    Parameters.global_material_balance = global_material_balance
    Parameters.serialization = serialization
    Parameters.dynamization_activated = dynamization_activated
    Parameters.cleaned_opt_quantity = cleaned_opt_quantity
    Parameters.capped_prices = capped_prices
    Parameters.verbose_optimization_logger = verbose_optimization_logger
    Parameters.verbose_calculation_logger = verbose_calculation_logger
    Parameters.activate_add_on_cmodule = activate_cmodule
    Parameters.chart_flag = show_dashboard

    run_timba(Parameters=Parameters,folderpath=folderpath)
    run_extensions(UserIO=Parameters)

#Dashboard command
@cli.command("dashboard")
@click.option(
    '-NF', '--num_files', 
    default=2, 
    show_default=True, 
    type=int, 
    help="Number of .pkl files to read"
)

@click.option(
    '-DP', '--data_folderpath', 
    required=False, 
    type=click.Path(
        file_okay=False,
        writable=True, 
        path_type=Path
    ), 
    default=Path.cwd(),
    show_default=f"current working directory: {Path.cwd()}",
    help="Path to directory with Input/Output folder."
)

def dashboard_cli(num_files, data_folderpath):  
    """toolkit for analysing TiMBA's simulation results"""  
    from TiMBA.parameters.paths import OUTPUT_DIR, ADDINFOPTHTOOLBOX, DATA_FOLDER
    SC_FOLDER = Path(DATA_FOLDER) / Path(OUTPUT_DIR)
    ADDINFO_FOLDER = Path(DATA_FOLDER) / Path(ADDINFOPTHTOOLBOX)
    click.echo(data_folderpath / SC_FOLDER)
    click.echo(data_folderpath / ADDINFO_FOLDER)
    td = timba_dashboard(
        num_files_to_read=num_files,
        FOLDER_PATH=data_folderpath,
        SCENARIO_PATH=SC_FOLDER,
        ADDINFO_PATH=ADDINFO_FOLDER,
    )
    try:
        td.run()
    except Exception as e:
        print(traceback.format_exc())
        #click.echo(f"No data found at: {SC_FOLDER}. Please, check if the TiMBA output is stored at this directory.")

# Load data command
@cli.command("load")
@click.option(
    '-U', '--user', 
    default=GIT_USER, 
    show_default=True, 
    required=True,
    help="Name of the GitHub user who stored the data."
)

@click.option(
    '-R', '--repo', 
    default=GIT_REPO, 
    show_default=True, 
    required=True,
    help="Name of the GitHub repository where stored the data."
)

@click.option(
    '-B', '--branch', 
    default=GIT_BRANCH, 
    show_default=True, 
    required=True,
    help="Name of the branch where stored the data."
)

@click.option(
    '-F', '--folder', 
    default=GIT_FOLDER, 
    show_default=True, 
    required=True,
    help="folder at GitHub where data is stored."
)

@click.option(
    '-FP', '--folderpath', 
    default=Path.cwd(), 
    show_default=f"current working directory: {Path.cwd()}",
    required=True, 
    help="The destination where the data should be copied to."
)

def load_data_cli(user, repo, branch, folder, folderpath):
    """load input data from web-based data hub"""

    dest_path = Path(folderpath) / DESTINATION_PATH
    print("destination path: ", dest_path)
    check_and_load_data(
        user=user,
        repo=repo,
        branch=branch,
        source_folder=folder,
        dest_folder=dest_path,
        check_flag=True,
        load_flag=True
    )


# Carbon Module command
@cli.command("carbon")
@click.option('-SC', '--sc_num', "sc_num",
              default=user_input[ParamNames.sc_num.value], show_default=True, required=True, type=int,
              help='Flag to control the number of processed scenarios.'
              )
@click.option('-CF_AGB', '--calc_c_forest_agb', 'calc_c_forest_agb',
              default=user_input[ParamNames.calc_c_forest_agb.value], show_default=True, required=True,
              type=bool,
              help='''Flag to activate carbon calculation
              for aboveground forest biomass.'''
              )
@click.option('-CF_BGB', '--calc_c_forest_bgb', 'calc_c_forest_bgb',
              default=user_input[ParamNames.calc_c_forest_bgb.value], show_default=True, required=True,
              type=bool,
              help='''Flag to activate carbon calculation
              for belowground forest biomass.'''
              )
@click.option('-CF_S', '--calc_c_forest_soil', 'calc_c_forest_soil',
              default=user_input[ParamNames.calc_c_forest_soil.value], show_default=True, required=True,
              type=bool,
              help='Flag to activate carbon calculation for forest soil.'
              )
@click.option('-CF_DWL', '--calc_c_forest_dwl', 'calc_c_forest_dwl',
              default=user_input[ParamNames.calc_c_forest_dwl.value], show_default=True, required=True,
              type=bool,
              help='''Flag to activate carbon calculation
              for dead wood and litter.'''
              )
@click.option('-C_HWP', '--calc_c_hwp', "calc_c_hwp",
              default=user_input[ParamNames.calc_c_hwp.value], show_default=True, required=True,
              type=bool,
              help='''Flag to activate carbon calculation
              for harvested wood products.'''
              )
@click.option('-C_HWP_A', '--c_hwp_accounting_approach',
              "c_hwp_accounting_approach",
              default=user_input[ParamNames.c_hwp_accounting_approach.value], show_default=True,
              required=True,
              type=str,
              help='''Flag to select the accounting approach
              for carbon in harvested wood products.'''
              )
@click.option('-R', '--read_in_pkl', 'read_in_pkl',
              default=user_input[ParamNames.read_in_pkl.value], show_default=True, required=True, type=bool,
              help='''Flag to control if pkl-
              or csv-files are read; reads in if True.'''
              )
@click.option('-SD', '--show_carbon_dashboard', 'show_carbon_dashboard',
              default=user_input[ParamNames.show_carbon_dashboard.value], show_default=True, required=False, type=bool,
              help="Flag to launch carbon dashboard.")

def carbon_cli(calc_c_forest_agb, sc_num, calc_c_forest_bgb, calc_c_forest_soil, calc_c_forest_dwl, calc_c_hwp,
               c_hwp_accounting_approach, read_in_pkl, show_carbon_dashboard):
    """calculate carbon stocks in forests and harvested wood products"""

    user_input_cli = {
        #ParamNames.activate_cmodule.value: activate_add_on_cmodule,
        ParamNames.sc_num.value: sc_num,
        ParamNames.read_in_pkl.value: read_in_pkl,
        ParamNames.calc_c_forest_agb.value: calc_c_forest_agb,
        ParamNames.calc_c_forest_bgb.value: calc_c_forest_bgb,
        ParamNames.calc_c_forest_soil.value: calc_c_forest_soil,
        ParamNames.calc_c_forest_dwl.value: calc_c_forest_dwl,
        ParamNames.calc_c_hwp.value: calc_c_hwp,
        ParamNames.c_hwp_accounting_approach.value: c_hwp_accounting_approach,
        ParamNames.show_carbon_dashboard.value: show_carbon_dashboard,
        # Adavanced settings not available via CLI
        #ParamNames.historical_c_hwp.value: historical_c_hwp,
        #ParamNames.hist_hwp_start_year.value: hist_hwp_start_year,
        #ParamNames.hist_hwp_start_year_default.value: (
        #    hist_hwp_start_year_default),
        #ParamNames.fao_data_update.value: fao_data_update
    }

    c_module = C_Module(UserInput=user_input_cli)
    c_module.run()
