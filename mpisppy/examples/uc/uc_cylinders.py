# This software is distributed under the 3-clause BSD License.

# TBD: put in more options: threads, mipgaps for spokes

# There is  manipulation of the mip gap,
#  so we need modifications of the vanilla dicts.
# Notice also that this uses MutliPHExtensions
import sys
import json
import mpisppy.examples.uc.uc_funcs as uc

from mpisppy.utils.sputils import spin_the_wheel
from mpisppy.extensions.extension import MultiPHExtension
from mpisppy.extensions.fixer import Fixer
from mpisppy.extensions.mipgapper import Gapper
from mpisppy.examples import baseparsers
from mpisppy.examples import vanilla


def _parse_args():
    parser = baseparsers.make_parser("uc_cylinders")
    parser = baseparsers.two_sided_args(parser)
    parser = baseparsers.fixer_args(parser)
    parser = baseparsers.fwph_args(parser)
    parser = baseparsers.lagrangian_args(parser)
    parser = baseparsers.xhatlooper_args(parser)
    parser = baseparsers.xhatshuffle_args(parser)
    parser = baseparsers.cross_scenario_cuts_args(parser)
    parser.add_argument("--ph-mipgaps-json",
                        help="json file with mipgap schedule (default None)",
                        dest="ph_mipgaps_json",
                        type=str,
                        default=None)                
    
    args = parser.parse_args()
    return args


def main():
    
    args = _parse_args()

    num_scen = args.num_scens

    with_fwph = args.with_fwph
    with_xhatlooper = args.with_xhatlooper
    with_xhatshuffle = args.with_xhatshuffle
    with_lagrangian = args.with_lagrangian
    with_fixer = args.with_fixer
    fixer_tol = args.fixer_tol
    with_cross_scenario_cuts = args.with_cross_scenario_cuts

    scensavail = [3,5,10,25]
    if num_scen not in scensavail:
        raise RuntimeError("num-scen was {}, but must be in {}".\
                           format(num_scen, scensavail))
    
    cb_data = {"scenario-count": num_scen,
               "path": str(num_scen)+"scenarios_r1"}
    scenario_creator = uc.scenario_creator
    scenario_denouement = uc.scenario_denouement
    all_scenario_names = [f"Scenario{i+1}" for i in range(num_scen)]
    rho_setter = uc._rho_setter
    
    # Things needed for vanilla cylinders
    beans = (args, scenario_creator, scenario_denouement, all_scenario_names)

    ### start ph spoke ###
    # Start with Vanilla PH hub
    hub_dict = vanilla.ph_hub(*beans,
                              cb_data=cb_data,
                              ph_extensions=MultiPHExtension,
                              rho_setter = rho_setter)
    # Extend and/or correct the vanilla dictionary
    if with_fixer:
        multi_ext = {"ext_classes": [Fixer, Gapper]}
    else:
        multi_ext = {"ext_classes": [Gapper]}
    if with_cross_scenario_cuts:
        multi_ext["ext_classes"].append(CrossScenarioExtension)
    else:
        
    hub_dict["opt_kwargs"]["PH_extension_kwargs"] = multi_ext
    if with_cross_scenario_cuts:
        hub_dict["opt_kwargs"]["PHoptions"]["cross_scen_options"]\
            = {"check_bound_improve_iterations" : args.cross_scenario_iter_cnt}

    if with_fixer:
        hub_dict["opt_kwargs"]["PHoptions"]["fixeroptions"] = {
            "verbose": args.with_verbose,
            "boundtol": fixer_tol,
            "id_fix_list_fct": uc.id_fix_list_fct,
        }
    if args.ph_mipgaps_json is not None:
        with open(args.ph_mipgaps_json) as fin:
            din = json.load(fin)
        mipgapdict = {int(i): din[i] for i in din}
    else:
        mipgapdict = None
    hub_dict["opt_kwargs"]["PHoptions"]["gapperoptions"] = {
        "verbose": args.with_verbose,
        "mipgapdict": mipgapdict
        }
        
    if args.default_rho is None:
        # since we are using a rho_setter anyway
        hub_dict.opt_kwargs.PHoptions["defaultPHrho"] = 1  
    ### end ph spoke ###
    
    # FWPH spoke
    if with_fwph:
        fw_spoke = vanilla.fwph_spoke(*beans, cb_data=cb_data)

    # Standard Lagrangian bound spoke
    if with_lagrangian:
        lagrangian_spoke = vanilla.lagrangian_spoke(*beans,
                                              cb_data=cb_data,
                                              rho_setter = rho_setter)

    # xhat looper bound spoke
    if with_xhatlooper:
        xhatlooper_spoke = vanilla.xhatlooper_spoke(*beans, cb_data=cb_data)

    # xhat shuffle bound spoke
    if with_xhatshuffle:
        xhatshuffle_spoke = vanilla.xhatshuffle_spoke(*beans, cb_data=cb_data)
       
    # cross scenario cut spoke
    if with_cross_scenario_cuts:
        cross_scenario_cut_spoke = vanilla.cross_scenario_cut_spoke(*beans, cb_data=cb_data)

    list_of_spoke_dict = list()
    if with_fwph:
        list_of_spoke_dict.append(fw_spoke)
    if with_lagrangian:
        list_of_spoke_dict.append(lagrangian_spoke)
    if with_xhatlooper:
        list_of_spoke_dict.append(xhatlooper_spoke)
    if with_xhatshuffle:
        list_of_spoke_dict.append(xhatshuffle_spoke)
    if with_cross_scenario_cuts:
        list_of_spoke_dict.append(cross_scenario_cut_spoke)

    spin_the_wheel(hub_dict, list_of_spoke_dict)


if __name__ == "__main__":
    main()
