#!/usr/bin/env python3
"""
Reviewed and Approved API Name Mappings for USDA Commodities

This file is the single source of truth for:

  OFFICIAL_API_MAPPINGS  — NASS commodity code name  →  QuickStats commodity_desc
                           Reviewed and approved entries written to usda_commodity.api_name
                           in the database.

  DISABLED_API_MAPPINGS  — Names explicitly excluded from DB population.
                           Use this instead of commenting out uncertain entries.
                           api_name will remain NULL for these in the database.

To build a full draft covering all ~400 NASS commodity codes, run:

    python reviewed_api_mappings.py

    # With QuickStats API key to validate guesses against the live API name list:
    python reviewed_api_mappings.py --api-key YOUR_KEY

    # Write draft to a file for easier editing:
    python reviewed_api_mappings.py --api-key YOUR_KEY --output draft_additions.py

Workflow for initial full build:
    1. Run the command above and review the printed table.
    2. Paste the OFFICIAL_API_MAPPINGS additions block below, correcting any
       entries flagged '← VALIDATE'.
    3. Move any entries you are uncertain about to DISABLED_API_MAPPINGS with
       a reason string, e.g. 'uncertain - revisit' or 'not a QuickStats commodity'.
    4. Run:  python interactive_commodity_mapper.py --apply-api-names
"""

import re
from typing import Dict, Optional

# ============================================================================
# OFFICIAL: reviewed and approved  (NASS code name → QuickStats commodity_desc)
# ============================================================================

OFFICIAL_API_MAPPINGS: Dict[str, str] = {
'ALL GRAPES': 'GRAPES',
    'ALMONDS': 'ALMONDS',
    'CORN  ALL': 'CORN',
    'CUCUMBERS': 'CUCUMBERS',
    'OLIVES': 'OLIVES',
    'PEACHES': 'PEACHES',
    'PISTACHIO NUTS': 'PISTACHIOS',
    'POTATOES  ALL': 'POTATOES',
    'RICE  ALL': 'RICE',
    'SWEETPOTATOES': 'SWEET POTATOES',
    'TOMATOES': 'TOMATOES',
    'WALNUTS (ENGLISH)': 'WALNUTS',
    'WHEAT': 'WHEAT',
    'ALL PEARS': 'PEARS',
    'ALL SHEEP': 'SHEEP',
    'APPLES': 'APPLES',
    'APRICOTS': 'APRICOTS',
    'ASPARAGUS': 'ASPARAGUS',
    'AVOCADOS': 'AVOCADOS',
    'BANANAS': 'BANANAS',
    'BARLEY  ALL': 'BARLEY',
    'BEANS  ALL DRY EDIBLE': 'BEANS',
    'BEEF': 'BEEF',
    'BEETS': 'BEETS',
    'BISON': 'BISON',
    'BLACKBERRIES': 'BLACKBERRIES',
    'BLUEBERRIES': 'BLUEBERRIES',
    'BOYSENBERRIES': 'BOYSENBERRIES',
    'BROCCOLI': 'BROCCOLI',
    'BRUSSELS SPROUTS': 'BRUSSELS SPROUTS',
    'BUTTER': 'BUTTER',
    'BUTTERMILK  DRY  TOTAL': 'BUTTERMILK',
    'CABBAGE': 'CABBAGE',
    'CANEBERRIES': 'CANEBERRIES',
    'CANOLA': 'CANOLA',
    'CARROTS': 'CARROTS',
    'CATTLE': 'CATTLE',
    'CAULIFLOWER': 'CAULIFLOWER',
    'CELERY': 'CELERY',
    'CHEESE  AMERICAN  WHOLE MILK  TOTAL': 'CHEESE',
    'COFFEE': 'COFFEE',
    'COTTON  ALL LINT (GINNED)': 'COTTON',
    'CRANBERRIES': 'CRANBERRIES',
    'DATES': 'DATES',
    'DUCKS': 'DUCKS',
    'EQUINE': 'EQUINE',
    'FIGS': 'FIGS',
    'FLAXSEED': 'FLAXSEED',
    'GARLIC': 'GARLIC',
    'GINGER ROOT': 'GINGER ROOT',
    'GOATS': 'GOATS',
    'GUAVAS': 'GUAVAS',
    'HAY  ALL (DRY)': 'HAY',
    'HAZELNUTS': 'HAZELNUTS',
    'HOGS': 'HOGS',
    'HOPS': 'HOPS',
    'ICE CREAM  LOWFAT  TOTAL': 'ICE CREAM',
    'K-EARLY CITRUS': 'K-EARLY CITRUS',
    'KIWIFRUIT': 'KIWIFRUIT',
    'LAMB & MUTTON': 'LAMB & MUTTON',
    'LEMONS': 'LEMONS',
    'LENTILS': 'LENTILS',
    'LOGANBERRIES': 'LOGANBERRIES',
    'MACADAMIAS': 'MACADAMIAS',
    'MAPLE SYRUP': 'MAPLE SYRUP',
    'MILK  DRY  WHOLE': 'MILK',
    'MILLET (PROSO)': 'MILLET',
    'MOHAIR': 'MOHAIR',
    'MUSTARD': 'MUSTARD',
    'NECTARINES': 'NECTARINES',
    'OATS': 'OATS',
    'OKRA': 'OKRA',
    'ONIONS': 'ONIONS',
    'ORANGES ALL EXCEPT TEMPLES': 'ORANGES',  # NASS subcategory; QuickStats commodity_desc is ORANGES
    'PAPAYAS': 'PAPAYAS',
    'PEANUTS': 'PEANUTS',
    'PEAS  DRY EDIBLE': 'PEAS',
    'PECANS': 'PECANS',
    'PINEAPPLES': 'PINEAPPLES',
    'PLUMS': 'PLUMS',
    'PORK': 'PORK',
    'PUMPKINS': 'PUMPKINS',
    'RADISHES': 'RADISHES',
    'RAPESEED': 'RAPESEED',
    'RYE': 'RYE',
    'SAFFLOWER': 'SAFFLOWER',
    'SORGHUM  ALL': 'SORGHUM',
    'SOYBEANS': 'SOYBEANS',
    'SPINACH': 'SPINACH',
    'SQUASH': 'SQUASH',
    'STRAWBERRIES': 'STRAWBERRIES',
    'SUGARBEETS': 'SUGARBEETS',
    'SUGARCANE  FOR SEED': 'SUGARCANE',
    'TANGELOS': 'TANGELOS',
    'TANGERINES': 'TANGERINES',
    'TARO': 'TARO',
    'VEAL': 'VEAL',
    'WATER ICES': 'WATER ICES',
    'WHEY  CONDENSED  TOTAL': 'WHEY',
    'WOOL': 'WOOL',
    'YOGURT  FROZEN  TOTAL': 'YOGURT',
    'ALPACAS': 'ALPACAS',
    'AMARANTH': 'AMARANTH',
    'ARTICHOKES': 'ARTICHOKES',
    'BASIL': 'BASIL',
    'BEESWAX': 'BEESWAX',
    'BITTERMELON': 'BITTERMELON',
    'BUCKWHEAT': 'BUCKWHEAT',
    'CACAO': 'CACAO',
    'CAMELINA': 'CAMELINA',
    'CASSAVA': 'CASSAVA',
    'CHERIMOYAS': 'CHERIMOYAS',
    'CHESTNUTS': 'CHESTNUTS',
    'CHICKENS': 'CHICKENS',
    'CHICKPEAS': 'CHICKPEAS',
    'CHIRONJAS': 'CHIRONJAS',
    'CHUKARS': 'CHUKARS',
    'CILANTRO': 'CILANTRO',
    'CITRONS': 'CITRONS',
    'COCONUTS': 'COCONUTS',
    'CORIANDER': 'CORIANDER',
    'CRAMBE': 'CRAMBE',
    'CREAM': 'CREAM',
    'CURRANTS': 'CURRANTS',
    'DAIKON': 'DAIKON',
    'DEER': 'DEER',
    'DILL': 'DILL',
    'DRAGON FRUIT': 'DRAGON FRUIT',
    'EGGPLANT': 'EGGPLANT',
    'EGGS': 'EGGS',
    'ELDERBERRIES': 'ELDERBERRIES',
    'ELK': 'ELK',
    'EMUS': 'EMUS',
    'ESCAROLE & ENDIVE': 'ESCAROLE & ENDIVE',
    'GEESE': 'GEESE',
    'GINSENG': 'GINSENG',
    'GOOSEBERRIES': 'GOOSEBERRIES',
    'GOURDS': 'GOURDS',
    'GRAPEFRUIT': 'GRAPEFRUIT',
    'GUAR': 'GUAR',
    'GUINEAS': 'GUINEAS',
    'HEMP': 'HEMP',
    'HONEY': 'HONEY',
    'HORSERADISH': 'HORSERADISH',
    'JICAMA': 'JICAMA',
    'JOJOBA': 'JOJOBA',
    'KAVA': 'KAVA',
    'KUMQUATS': 'KUMQUATS',
    'LARD': 'LARD',
    'LAUPELE': 'LAUPELE',
    'LEMONS & LIMES': 'LEMONS & LIMES',
    'LETTUCE': 'LETTUCE',
    'LIMES': 'LIMES',
    'LLAMAS': 'LLAMAS',
    'LONGAN': 'LONGAN',
    'LOTUS ROOT': 'LOTUS ROOT',
    'LYCHEES': 'LYCHEES',
    'MANGOES': 'MANGOES',
    'MELONS': 'MELONS',
    'MINK': 'MINK',
    'MINT': 'MINT',
    'MISCANTHUS': 'MISCANTHUS',
    'MOUNTAIN APPLES': 'MOUNTAIN APPLES',
    'MULBERRIES': 'MULBERRIES',
    'MUSHROOMS': 'MUSHROOMS',
    'OSTRICHES': 'OSTRICHES',
    'PARSLEY': 'PARSLEY',
    'PARSNIPS': 'PARSNIPS',
    'PARTRIDGES': 'PARTRIDGES',
    'PASSION FRUIT': 'PASSION FRUIT',
    'PEAFOWL': 'PEAFOWL',
    'PEPPERS': 'PEPPERS',
    'PERSIMMONS': 'PERSIMMONS',
    'PHEASANTS': 'PHEASANTS',
    'PLANTAINS': 'PLANTAINS',
    'PLUM-APRICOT HYBRIDS': 'PLUM-APRICOT HYBRIDS',
    'PLUMS & PRUNES': 'PLUMS & PRUNES',
    'POMEGRANATES': 'POMEGRANATES',
    'POPCORN': 'POPCORN',
    'PRUNES': 'PRUNES',
    'QUAIL': 'QUAIL',
    'QUENEPAS': 'QUENEPAS',
    'RAMBUTAN': 'RAMBUTAN',
    'RASPBERRIES': 'RASPBERRIES',
    'RHEAS': 'RHEAS',
    'RHUBARB': 'RHUBARB',
    'SESAME': 'SESAME',
    'SOURSOPS': 'SOURSOPS',
    'SPROUTS': 'SPROUTS',
    'STARFRUIT': 'STARFRUIT',
    'SUNFLOWER': 'SUNFLOWER',
    'SWEET CORN': 'SWEET CORN',
    'SWEET RICE': 'SWEET RICE',
    'SWEETSOPS': 'SWEETSOPS',
    'SWITCHGRASS': 'SWITCHGRASS',
    'TALLOW': 'TALLOW',
    'TART CHERRIES': 'CHERRIES',
    'TEMPLES': 'TEMPLES',
    'TOBACCO': 'TOBACCO',
    'TRITICALE': 'TRITICALE',
    'TURKEYS': 'TURKEYS',
    'TURNIPS': 'TURNIPS',
    'WATERCRESS': 'WATERCRESS',
    'WILD RICE': 'WILD RICE',
    'YAMS': 'YAMS',

}

# ============================================================================
# DISABLED: reviewed but excluded from DB population
#
# Use this for entries you have reviewed and decided should NOT get an api_name
# in the database.  api_name will remain NULL for these rows.
#
# Reasons to disable:
#   - Aggregate / meta-category with no direct QuickStats commodity_desc
#     (e.g. 'CROP FARMS', 'FARM OPERATIONS')
#   - Uncertain mapping that needs more investigation
#   - Out-of-scope for current ETL pipeline
#
# Format: { nass_code_name: 'reason string' }
# DO NOT put entries here that belong in OFFICIAL_API_MAPPINGS.
# ============================================================================

DISABLED_API_MAPPINGS: Dict[str, str] = {
'10 MAJOR VEGETABLES (VARIES BY SEASON)': 'not in QuickStats API list',
    '12 MAJOR VEGETABLES (VARIES BY SEASON)': 'not in QuickStats API list',
    '13 MAJOR VEGETABLES (VARIES BY SEASON)': 'not in QuickStats API list',
    '25 MAJOR VEGETABLES (VARIES BY SEASON)': 'not in QuickStats API list',
    '3 MAJOR VEGETABLES (VARIES BY SEASON)': 'not in QuickStats API list',
    '34 MAJOR VEGETABLES (VARIES BY SEASON)': 'not in QuickStats API list',
    '9 MAJOR VEGETABLES (VARIES BY SEASON)': 'not in QuickStats API list',
    'ALFALFA & ALFALFA MIXTURES - NEW SEEDINGS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ALL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ALL COWS': 'not in QuickStats API list',  # heuristic guess: 'COWS' — verify before moving to OFFICIAL
    'ALL FARMS': 'not in QuickStats API list',  # heuristic guess: 'FARMS' — verify before moving to OFFICIAL
    'ALL NONCITRUS': 'not in QuickStats API list',  # heuristic guess: 'NONCITRUS' — verify before moving to OFFICIAL
    'ALL NUTS': 'not in QuickStats API list',  # heuristic guess: 'NUTS' — verify before moving to OFFICIAL
    'ANGORA': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ARTICHOKE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BARROWS & GILTS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BARTLETT PEARS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BEANS GARBANZO (CHICK PEAS)': 'not in QuickStats API list',  # heuristic guess: 'BEANS GARBANZO' — verify before moving to OFFICIAL
    'BEANS GARBANZO (LARGE)': 'not in QuickStats API list',  # heuristic guess: 'BEANS GARBANZO' — verify before moving to OFFICIAL
    'BEANS-DRY EDIBLE - LIMA-ALL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BEANS-DRY EDIBLE - WHITE - SMALL FLAT': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BEANS-LIMA': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BEANS-LIMA - BABY': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BEANS-LIMA - FORDHOOK': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BEANS-SNAP': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BEEF COW REPLACEMENT HEIFERS TO CALVE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BLACK RASPBERRIES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BREEDING': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BREEDING EWES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BREEDING RAMS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BREEDING TOTAL SHEEP & LAMB': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BULLS & STAGS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'BULLS 500+ LBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CALF CROP': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CALVES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CALVES  OTHER HEIFERS  STEERS 500+': 'not in QuickStats API list',  # heuristic guess: 'CALVES' — verify before moving to OFFICIAL
    'CALVES LESS THAN 500 LBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CAPACITY  STORAGE': 'not in QuickStats API list',  # heuristic guess: 'CAPACITY' — verify before moving to OFFICIAL
    'CATTLE & CALVES - ALL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CATTLE 500+ LBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CATTLE ON FEED': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHEDDAR CHEESE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHICKEN HATCHERIES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHICKENS - EXCLUDING COMMERCIAL BROILERS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHICKENS ANNUAL-ALL EXCL. COMM BROILERS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHICKENS-HATCHING BROILER TYPE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHICKENS-HATCHING EGG TYPE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHICKENS-HATCHING TYPE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHICKENS-TABLE EGG TYPE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CHILE PEPPERS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CITRUS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CLINGSTONE PEACHES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'COLLARDS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'COMMERCIAL VEGETABLES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CONCORD GRAPES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CORN-SWEET': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'COWS & HEIFERS THAT CALVED': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'COWS THAT CALVED - BEEF': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'COWS THAT CALVED - MILK': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'CROP FARMS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'DAIRY COWS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'DRY WHEY FOR HUMAN CONSUMPTION': 'not in QuickStats API list',  # heuristic guess: 'DRY WHEY' — verify before moving to OFFICIAL
    'EGG PLANT': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ESCAROLE/ENDIVE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'FARM NUMBERS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'FIELD & MISC CROPS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'FORAGE  ALFALFA(DRY HAY+HAYLAGE)': 'not in QuickStats API list',  # heuristic guess: 'FORAGE' — verify before moving to OFFICIAL
    'FORAGE  ALL(DRY HAY+HAYLAGE)': 'not in QuickStats API list',  # heuristic guess: 'FORAGE' — verify before moving to OFFICIAL
    'FREESTONE PEACHES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'FROZEN DAIRY PRODUCTS  OTHER': 'not in QuickStats API list',  # heuristic guess: 'FROZEN DAIRY PRODUCTS' — verify before moving to OFFICIAL
    'FRUITS & NUTS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'GRAPEFRUIT ALL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'GRAPEFRUIT COLOR SEEDLESS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'GRAPEFRUIT OTHER': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'GRAPEFRUIT WHITE SEEDLESS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'GREEN PEAS FOR PROCESSING': 'not in QuickStats API list',  # heuristic guess: 'GREEN PEAS' — verify before moving to OFFICIAL
    'HAY COWPEA': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HAY SOYBEAN': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HAY SWEET CLOVER': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HEAVY MATURE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HEIFERS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HEIFERS 500+ LBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HEIFERS 500+ LBS - BEEF REPL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HEIFERS 500+ LBS - MILK REPL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'HEIFERS 500+ LBS - OTHER': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ICE CREAM MIX PRODUCED': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'IMPROVED PECANS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'KALE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'LACTOSE  ANIMAL': 'not in QuickStats API list',  # heuristic guess: 'LACTOSE' — verify before moving to OFFICIAL
    'LACTOSE  HUMAN': 'not in QuickStats API list',  # heuristic guess: 'LACTOSE' — verify before moving to OFFICIAL
    'LACTOSE  TOTAL': 'not in QuickStats API list',  # heuristic guess: 'LACTOSE' — verify before moving to OFFICIAL
    'LAMB CROP': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'LAMBS & YEARLINGS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'LIGHT MATURE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'LIVESTOCK FARMS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MAJOR DECIDUOUS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MANUFACTURED DAIRY PRODUCTS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MARKET': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MARKET LAMBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MARKET SHEEP': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MARKET TOTAL SHEEP & LAMB': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MATURE SHEEP': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MELLORINE MIX PRODUCED': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MELONS - HONEYBALL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MELONS CANTALOUPE-HONEYDEW-WATERMELON': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MELONS-CANTALOUPES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MELONS-HONEYDEW': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MELONS-WATERMELON': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MILK COW REPLACEMENT HEIFERS TO CALVE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MILK COWS & PRODUCTION': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MILK SHERBET  HARD': 'not in QuickStats API list',  # heuristic guess: 'MILK SHERBET' — verify before moving to OFFICIAL
    'MILK SHERBET  TOTAL': 'not in QuickStats API list',  # heuristic guess: 'MILK SHERBET' — verify before moving to OFFICIAL
    'MILK SHERBET MIX PRODUCED': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MISC. NONCITRUS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'MUSHROOMS ALL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'NATIVE PECANS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'NIAGARA GRAPES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'NONFAT DRY MILK FOR HUMAN CONSUMPTION': 'not in QuickStats API list',  # heuristic guess: 'NONFAT DRY MILK' — verify before moving to OFFICIAL
    'NUMBER OF PIGS PER LITTER': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'OLD': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ONIONS - SPRING': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ONIONS - SUMMER': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ONIONS - SUMMER NON-STORAGE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ONIONS - SUMMER STORAGE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'OPERATIONS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ORANGES TEMPLES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'ORANGES VALENCIA': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'OTHER COWS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'OTHER PEARS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'OTHER POULTRY': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'PASTURE AND RANGE CONDITION': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'PEA SEED  WRINKLED': 'not in QuickStats API list',  # heuristic guess: 'PEA SEED' — verify before moving to OFFICIAL
    'PEAS AUSTRIAN WINTER': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'PEAS-DRY EDIBLE -  SMOOTH GREEN': 'not in QuickStats API list',  # heuristic guess: 'PEAS-DRY EDIBLE -' — verify before moving to OFFICIAL
    'PEAS-DRY EDIBLE -  YELLOW & WHITE': 'not in QuickStats API list',  # heuristic guess: 'PEAS-DRY EDIBLE -' — verify before moving to OFFICIAL
    'PEAS-GREEN': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'PICKLE STOCKS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'PIG CROP (1000 HEAD)': 'not in QuickStats API list',  # heuristic guess: 'PIG CROP' — verify before moving to OFFICIAL
    'PRINCIPAL CROPS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'PROCESSED CHEESE  COLD PACK  CHEESE FOODS  TOTAL': 'not in QuickStats API list',  # heuristic guess: 'PROCESSED CHEESE' — verify before moving to OFFICIAL
    'RAISIN GRAPES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'RED RASPBERRIES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'REPLACEMENT LAMBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SALES $10,000  TO  $39,999': 'not in QuickStats API list',  # heuristic guess: 'SALES $10,000' — verify before moving to OFFICIAL
    'SALES $100,000 TO $249,999': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SALES $250,000 +': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SALES $40,000  TO  $99,999': 'not in QuickStats API list',  # heuristic guess: 'SALES $40,000' — verify before moving to OFFICIAL
    'SALES LESS THAN    $10,000': 'not in QuickStats API list',  # heuristic guess: 'SALES LESS THAN' — verify before moving to OFFICIAL
    'SHALLOTS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SHEEP & LAMB OPERATIONS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SHEEP & LAMBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SHEEP ON FEED': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SNAP BEANS FOR PROCESSING': 'not in QuickStats API list',  # heuristic guess: 'SNAP BEANS' — verify before moving to OFFICIAL
    'SOWS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SOWS AND GILTS BRED': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'SOWS FARROWED (1000 HEAD)': 'not in QuickStats API list',  # heuristic guess: 'SOWS FARROWED' — verify before moving to OFFICIAL
    'STAGS & BOARS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'STEERS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'STEERS 500+ LBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'STEERS AND HEIFERS 500+ LBS': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TABLE GRAPES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TOBACCO AIR-CURED ALL (CLASS 3)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED ALL' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED DARK ALL (CLASS 3B)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED DARK ALL' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED DARK GREEN RIVER BELT (TYPE 36)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED DARK GREEN RIVER BELT' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED DARK KY-TN (TYPE 35-36)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED DARK KY-TN' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED DARK ONE-SUCKER BELT (TYPE 35)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED DARK ONE-SUCKER BELT' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED DARK SUN-CURED BELT (TYPE 37)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED DARK SUN-CURED BELT' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED LIGHT ALL (CLASS 3A)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED LIGHT ALL' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED LIGHT BURLEY (TYPE 31)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED LIGHT BURLEY' — verify before moving to OFFICIAL
    'TOBACCO AIR-CURED LIGHT SOUTHERN MD BELT (TYPE 32)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO AIR-CURED LIGHT SOUTHERN MD BELT' — verify before moving to OFFICIAL
    'TOBACCO ALL  (ALL CLASSES)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO ALL' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER ALL (CLASS 5)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER ALL' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER CONN VALLEY (CLASS 5A)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER CONN VALLEY' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER CONN VALLEY BROADLEAF (TYPE 51)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER CONN VALLEY BROADLEAF' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER CONN VALLEY HAVANA SEED (TYPE 52)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER CONN VALLEY HAVANA SEED' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER GA-FL SHADE GROWN (TYPE 62)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER GA-FL SHADE GROWN' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER NORTHERN WISCONSIN (TYPE 55)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER NORTHERN WISCONSIN' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER SOUTHERN WISCONSIN (TYPE 54)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER SOUTHERN WISCONSIN' — verify before moving to OFFICIAL
    'TOBACCO CIGAR BINDER WISCONSIN (CLASS 5B)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR BINDER WISCONSIN' — verify before moving to OFFICIAL
    'TOBACCO CIGAR FILLER ALL (CLASS 4)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR FILLER ALL' — verify before moving to OFFICIAL
    'TOBACCO CIGAR FILLER OHIO-MIAMI VALLEY (TYPE 42-44)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR FILLER OHIO-MIAMI VALLEY' — verify before moving to OFFICIAL
    'TOBACCO CIGAR FILLER PA SEED LEAF (TYPE 41)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR FILLER PA SEED LEAF' — verify before moving to OFFICIAL
    'TOBACCO CIGAR TYPES ALL (CLASS 4-6)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR TYPES ALL' — verify before moving to OFFICIAL
    'TOBACCO CIGAR WRAPPER ALL (CLASS 6)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR WRAPPER ALL' — verify before moving to OFFICIAL
    'TOBACCO CIGAR WRAPPER CONN VALLEY SHADE-GROWN (TYPE 61)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO CIGAR WRAPPER CONN VALLEY SHADE-GROWN' — verify before moving to OFFICIAL
    'TOBACCO FIRE-CURED  KY-TN (TYPE 22-23)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FIRE-CURED' — verify before moving to OFFICIAL
    'TOBACCO FIRE-CURED ALL (CLASS 2)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FIRE-CURED ALL' — verify before moving to OFFICIAL
    'TOBACCO FIRE-CURED EASTERN DISTRICT (TYPE 22)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FIRE-CURED EASTERN DISTRICT' — verify before moving to OFFICIAL
    'TOBACCO FIRE-CURED HENDERSON BELT (TYPE 24)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FIRE-CURED HENDERSON BELT' — verify before moving to OFFICIAL
    'TOBACCO FIRE-CURED VA BELT (TYPE 21)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FIRE-CURED VA BELT' — verify before moving to OFFICIAL
    'TOBACCO FIRE-CURED WESTERN DISTRICT (TYPE 23)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FIRE-CURED WESTERN DISTRICT' — verify before moving to OFFICIAL
    'TOBACCO FLUE-CURED ALL (CLASS 1)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FLUE-CURED ALL' — verify before moving to OFFICIAL
    'TOBACCO FLUE-CURED EAST NC BELT (TYPE 12)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FLUE-CURED EAST NC BELT' — verify before moving to OFFICIAL
    'TOBACCO FLUE-CURED GA-FLA BELT (TYPE 14)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FLUE-CURED GA-FLA BELT' — verify before moving to OFFICIAL
    'TOBACCO FLUE-CURED NC BORD & SC BELT (TYPE 13)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FLUE-CURED NC BORD & SC BELT' — verify before moving to OFFICIAL
    'TOBACCO FLUE-CURED OLD/MID BELTS (TYPE 11)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO FLUE-CURED OLD/MID BELTS' — verify before moving to OFFICIAL
    'TOBACCO MISC DOMESTIC PERIQUE (TYPE 72)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO MISC DOMESTIC PERIQUE' — verify before moving to OFFICIAL
    'TOBACCO NON-CIGAR TYPES ALL (CLASS 1-3)': 'not in QuickStats API list',  # heuristic guess: 'TOBACCO NON-CIGAR TYPES ALL' — verify before moving to OFFICIAL
    'TOTAL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TOTAL MATURE': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TOTAL POULTRY': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TOTAL RED MEAT': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TURKEY HATCHERY': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TURKEYS - ALL': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TURKEYS - HEAVY': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TURKEYS - LIGHT': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'TURNIP': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'WHEY PROTEIN CONCENTRATE  ANIMAL': 'not in QuickStats API list',  # heuristic guess: 'WHEY PROTEIN CONCENTRATE' — verify before moving to OFFICIAL
    'WHEY PROTEIN CONCENTRATE  HUMAN': 'not in QuickStats API list',  # heuristic guess: 'WHEY PROTEIN CONCENTRATE' — verify before moving to OFFICIAL
    'WHEY SOLIDS IN WET BLENDS  ANIMAL': 'not in QuickStats API list',  # heuristic guess: 'WHEY SOLIDS IN WET BLENDS' — verify before moving to OFFICIAL
    'WHEY SOLIDS IN WET BLENDS  HUMAN': 'not in QuickStats API list',  # heuristic guess: 'WHEY SOLIDS IN WET BLENDS' — verify before moving to OFFICIAL
    'BETEL NUTS': 'not in QuickStats API list',  # Hawaii/Pacific crop — not a QuickStats commodity_desc
    'BREADFRUIT': 'not in QuickStats API list',  # Pacific crop — not a QuickStats commodity_desc
    'CARABAO': 'not in QuickStats API list',  # Hawaii water buffalo — not a QuickStats commodity_desc
    'CHICORY': 'not in QuickStats API list',  # not a QuickStats commodity_desc
    'CHIVES': 'not in QuickStats API list',  # not a QuickStats commodity_desc
    'RABBITS': 'not in QuickStats API list',  # not a QuickStats commodity_desc
    'WILD BLUEBERRIES': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'YOUNG': 'not in QuickStats API list',  # heuristic unchanged — find the correct QuickStats name
    'WINE GRAPES': "duplicate of 'ALL GRAPES' (both map to QuickStats 'GRAPES')",
    'CORN  FOR SILAGE': "duplicate of 'CORN  ALL' (both map to QuickStats 'CORN')",
    'CORN  FOR GRAIN': "duplicate of 'CORN  ALL' (both map to QuickStats 'CORN')",
    'COTTON  UPLAND': "duplicate of 'COTTON  ALL LINT (GINNED)' (both map to QuickStats 'COTTON')",
    'COTTON  AMER. PIMA': "duplicate of 'COTTON  ALL LINT (GINNED)' (both map to QuickStats 'COTTON')",
    'COTTON  SEED': "duplicate of 'COTTON  ALL LINT (GINNED)' (both map to QuickStats 'COTTON')",
    'HAY  ALFALFA (DRY)': "duplicate of 'HAY  ALL (DRY)' (both map to QuickStats 'HAY')",
    'HAY  OTHER (DRY)': "duplicate of 'HAY  ALL (DRY)' (both map to QuickStats 'HAY')",
    'HAY  WILD (DRY)': "duplicate of 'HAY  ALL (DRY)' (both map to QuickStats 'HAY')",
    'POTATOES  FALL': "duplicate of 'POTATOES  ALL' (both map to QuickStats 'POTATOES')",
    'POTATOES  SPRING': "duplicate of 'POTATOES  ALL' (both map to QuickStats 'POTATOES')",
    'POTATOES  SUMMER': "duplicate of 'POTATOES  ALL' (both map to QuickStats 'POTATOES')",
    'POTATOES  WINTER': "duplicate of 'POTATOES  ALL' (both map to QuickStats 'POTATOES')",
    'RICE  LONG GRAIN': "duplicate of 'RICE  ALL' (both map to QuickStats 'RICE')",
    'RICE  MED GRAIN': "duplicate of 'RICE  ALL' (both map to QuickStats 'RICE')",
    'RICE  MED-SHORT GRAIN': "duplicate of 'RICE  ALL' (both map to QuickStats 'RICE')",
    'RICE  SHORT GRAIN': "duplicate of 'RICE  ALL' (both map to QuickStats 'RICE')",
    'TOMATOES FOR PROCESSING': "duplicate of 'TOMATOES' (both map to QuickStats 'TOMATOES')",
    'WHEAT  ALL': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  DURUM': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  HARD RED ALL': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  OTHER SPRING': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  SPRING HARD RED': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  SPRING WHITE': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  WHITE ALL': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  WINTER ALL': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  WINTER HARD RED': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  WINTER SOFT RED': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'WHEAT  WINTER WHITE': "duplicate of 'WHEAT' (both map to QuickStats 'WHEAT')",
    'ALL GOATS': "duplicate of 'GOATS' (both map to QuickStats 'GOATS')",
    'ALL RASPBERRIES': "duplicate of 'RASPBERRIES' (both map to QuickStats 'RASPBERRIES')",
    'BARLEY  FEED': "duplicate of 'BARLEY  ALL' (both map to QuickStats 'BARLEY')",
    'BARLEY  MALTING': "duplicate of 'BARLEY  ALL' (both map to QuickStats 'BARLEY')",
    'BEANS  ALL RED KIDNEY': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  BABY LIMA': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  BLACK TURTLE SOUP': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  BLACKEYE': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  CRANBERRY': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  DARK RED KIDNEY': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  DRY EDIBLE OTHER THAN LIMA': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  GARBANZO': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  GREAT NORTHERN': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  LARGE LIMA': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  LIGHT RED KIDNEY': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  NAVY (PEA/BEANS)': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  OTHER DRY EDIBLE': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  PINK': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  PINTO': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  SMALL RED': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BEANS  SMALL WHITE': "duplicate of 'BEANS  ALL DRY EDIBLE' (both map to QuickStats 'BEANS')",
    'BUTTERMILK  CONDENSED & EVAPORATED': "duplicate of 'BUTTERMILK  DRY  TOTAL' (both map to QuickStats 'BUTTERMILK')",
    'BUTTERMILK  DRY  HUMAN': "duplicate of 'BUTTERMILK  DRY  TOTAL' (both map to QuickStats 'BUTTERMILK')",
    'CATTLE  ALL BEEF': "duplicate of 'CATTLE' (both map to QuickStats 'CATTLE')",
    'CHEESE  AMERICAN  COLBY & JACK & MONTEREY': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  AMERICAN  PART SKIM': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  BLUE & GORGONZOLA': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  BRICK': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  BRICK & MUENSTER  TOTAL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  COLD PACK & CHEESE FOODS': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  COTTAGE  CREAMED': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  COTTAGE  CURD': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  COTTAGE  LOWFAT': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  CREAM': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  CREAM AND NEUFCHATEL  TOTAL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  HISPANIC': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  HARD  PARMESAN AND SIMILARS': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  HARD  PROVOLONE AND SIMILARS': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  HARD  ROMANO AND SIMILARS': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  HARD  TOTAL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  OTHER  TOTAL  (TOTAL LESS  MOZZ.)': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  SOFT  MOZZARELLA': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  SOFT  OTHER': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  SOFT  RICOTTA AND SIMILARS': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  SOFT  TOTAL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  ITALIAN  TOTAL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  LIMBURGER': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  MUENSTER': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  NEUFCHATEL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  OTHER  TOTAL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  PROCESSED': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  PROCESSED  FOODS & SPREADS': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  SWISS': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'CHEESE  TOTAL': "duplicate of 'CHEESE  AMERICAN  WHOLE MILK  TOTAL' (both map to QuickStats 'CHEESE')",
    'ICE CREAM  HARD': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'ICE CREAM  LOWFAT  HARD': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'ICE CREAM  LOWFAT  MIX PRODUCED': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'ICE CREAM  LOWFAT  SOFT': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'ICE CREAM  NONFAT  HARD': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'ICE CREAM  NONFAT  MIX PRODUCED': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'ICE CREAM  NONFAT  TOTAL': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'ICE CREAM  TOTAL': "duplicate of 'ICE CREAM  LOWFAT  TOTAL' (both map to QuickStats 'ICE CREAM')",
    'MILK  CONDENSED  SKIM  SWEETENED  BULK': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  CONDENSED  SKIM  UNSWEETENED  BULK': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  CONDENSED  WHOLE  SWEETENED  BULK': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  CONDENSED  WHOLE  UNSWEETENED  BULK': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  DRY  SKIM  ANIMAL': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  DRY  WHOLE  PACKAGE 5+LBS.': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  SKIM  EVAPORATED  CASE': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  WHOLE  EVAP & SWEETENED COND CASE': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'MILK  WHOLE  EVAPORATED & CONDENSED  CASE': "duplicate of 'MILK  DRY  WHOLE' (both map to QuickStats 'MILK')",
    'ORANGES (MID & NAVEL)': "duplicate of 'ORANGES ALL EXCEPT TEMPLES' (both map to QuickStats 'ORANGES')",
    'ORANGES  ALL': "duplicate of 'ORANGES ALL EXCEPT TEMPLES' (both map to QuickStats 'ORANGES')",
    'PEANUTS  ALL': "duplicate of 'PEANUTS' (both map to QuickStats 'PEANUTS')",
    'PEAS  WRINKLED SEEDS': "duplicate of 'PEAS  DRY EDIBLE' (both map to QuickStats 'PEAS')",
    'SORGHUM  FOR GRAIN': "duplicate of 'SORGHUM  ALL' (both map to QuickStats 'SORGHUM')",
    'SORGHUM  FOR SILAGE': "duplicate of 'SORGHUM  ALL' (both map to QuickStats 'SORGHUM')",
    'SOYBEANS  ALL': "duplicate of 'SOYBEANS' (both map to QuickStats 'SOYBEANS')",
    'SUGARCANE  FOR SUGAR': "duplicate of 'SUGARCANE  FOR SEED' (both map to QuickStats 'SUGARCANE')",
    'SUGARCANE  FOR SUGAR AND SEED': "duplicate of 'SUGARCANE  FOR SEED' (both map to QuickStats 'SUGARCANE')",
    'SWEET CORN FOR PROCESSING': "duplicate of 'SWEET CORN' (both map to QuickStats 'SWEET CORN')",
    'WHEY  CONDENSED  SWEET  ANIMAL': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  CONDENSED  SWEET  HUMAN': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  DRY  ANIMAL': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  DRY  TOTAL': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  REDUCED LACTOSE  ANIMAL': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  REDUCED LACTOSE  HUMAN': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  REDUCED LACTOSE & MINERAL  ANIMAL': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  REDUCED LACTOSE & MINERAL  HUMAN': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  REDUCED LACTOSE & MINERAL  TOTAL': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  REDUCED MINERAL  ANIMAL': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'WHEY  REDUCED MINERAL  HUMAN': "duplicate of 'WHEY  CONDENSED  TOTAL' (both map to QuickStats 'WHEY')",
    'YOGURT  FROZEN  MIX PRODUCED': "duplicate of 'YOGURT  FROZEN  TOTAL' (both map to QuickStats 'YOGURT')",
    'YOGURT  FROZEN  NONFAT  HARD': "duplicate of 'YOGURT  FROZEN  TOTAL' (both map to QuickStats 'YOGURT')",
    'YOGURT  FROZEN  REG/LF  HARD': "duplicate of 'YOGURT  FROZEN  TOTAL' (both map to QuickStats 'YOGURT')",
    'YOGURT  PLAIN & FLAVORED': "duplicate of 'YOGURT  FROZEN  TOTAL' (both map to QuickStats 'YOGURT')",
    'CANTALOUPES': "duplicate of 'MELONS' (both map to QuickStats 'MELONS')",
    'HONEYDEW MELONS': "duplicate of 'MELONS' (both map to QuickStats 'MELONS')",
    'WATERMELONS': "duplicate of 'MELONS' (both map to QuickStats 'MELONS')",
    'LETTUCE  HEAD': "duplicate of 'LETTUCE' (both map to QuickStats 'LETTUCE')",
    'LETTUCE  LEAF': "duplicate of 'LETTUCE' (both map to QuickStats 'LETTUCE')",
    'LETTUCE  ROMAINE': "duplicate of 'LETTUCE' (both map to QuickStats 'LETTUCE')",
    'LETTUCE-HEAD': "duplicate of 'LETTUCE' (both map to QuickStats 'LETTUCE')",
    'LETTUCE-LEAF': "duplicate of 'LETTUCE' (both map to QuickStats 'LETTUCE')",
    'LETTUCE-ROMAINE': "duplicate of 'LETTUCE' (both map to QuickStats 'LETTUCE')",
    'MINT  PEPPERMINT': "duplicate of 'MINT' (both map to QuickStats 'MINT')",
    'MINT  SPEARMINT': "duplicate of 'MINT' (both map to QuickStats 'MINT')",
    'PEPPERMINT': "duplicate of 'MINT' (both map to QuickStats 'MINT')",
    'SPEARMINT': "duplicate of 'MINT' (both map to QuickStats 'MINT')",
    'PEPPERS  BELL': "duplicate of 'PEPPERS' (both map to QuickStats 'PEPPERS')",
    'PEPPERS  CHILI': "duplicate of 'PEPPERS' (both map to QuickStats 'PEPPERS')",
    'PEPPERS  OTHER': "duplicate of 'PEPPERS' (both map to QuickStats 'PEPPERS')",
    'PEPPERS-BELL': "duplicate of 'PEPPERS' (both map to QuickStats 'PEPPERS')",
    'PRUNES & PLUMS': "duplicate of 'PLUMS & PRUNES' (both map to QuickStats 'PLUMS & PRUNES')",
    'SUNFLOWER  ALL': "duplicate of 'SUNFLOWER' (both map to QuickStats 'SUNFLOWER')",
    'SUNFLOWER  NON-OIL TYPE': "duplicate of 'SUNFLOWER' (both map to QuickStats 'SUNFLOWER')",
    'SUNFLOWER  OIL TYPE': "duplicate of 'SUNFLOWER' (both map to QuickStats 'SUNFLOWER')",
    'SUNFLOWER SEED  ALL': "duplicate of 'SUNFLOWER' (both map to QuickStats 'SUNFLOWER')",
    'SUNFLOWER SEED  FOR OIL': "duplicate of 'SUNFLOWER' (both map to QuickStats 'SUNFLOWER')",
    'SUNFLOWER SEED  NON-OIL USE': "duplicate of 'SUNFLOWER' (both map to QuickStats 'SUNFLOWER')",
    'SWEET CHERRIES': "duplicate of 'TART CHERRIES' (both map to QuickStats 'CHERRIES')",
    'TOBACCO  AIR CURED': "duplicate of 'TOBACCO' (both map to QuickStats 'TOBACCO')",
    'TOBACCO  BURLEY': "duplicate of 'TOBACCO' (both map to QuickStats 'TOBACCO')",
    'TOBACCO  FIRE CURED': "duplicate of 'TOBACCO' (both map to QuickStats 'TOBACCO')",
    'TOBACCO  FLUE CURED': "duplicate of 'TOBACCO' (both map to QuickStats 'TOBACCO')",
    'CORN': "duplicate of 'CORN  ALL' (both map to QuickStats 'CORN')",
    'RICE': "duplicate of 'RICE  ALL' (both map to QuickStats 'RICE')",

}


# ============================================================================
# Runtime lookup
# ============================================================================

def guess_api_name(db_name: str) -> str:
    """
    Heuristic fallback: strip common NASS qualifier patterns to derive a likely API name.

    Handles the most common patterns in NASS commodity code naming:
        "CORN  ALL"               → "CORN"       (double-space subcategory)
        "HAY  ALFALFA (DRY)"      → "HAY"        (double-space + parenthetical)
        "POTATOES  ALL"           → "POTATOES"
        "TOMATOES FOR PROCESSING" → "TOMATOES"   (FOR ... suffix)
        "WALNUTS (ENGLISH)"       → "WALNUTS"    (parenthetical)
        "ALL GRAPES"              → "GRAPES"     (ALL prefix)
        "ALMONDS"                 → "ALMONDS"    (unchanged — already correct)

    Does NOT handle irregular cases like "PISTACHIO NUTS" → "PISTACHIOS" or
    "SWEETPOTATOES" → "SWEET POTATOES" — those must be added explicitly to
    OFFICIAL_API_MAPPINGS. Run --build-api-mappings to identify them.
    """
    name = db_name.strip()
    # Strip double-space subcategory: "CORN  ALL" → "CORN", "HAY  ALFALFA (DRY)" → "HAY"
    name = re.split(r'  ', name)[0].strip()
    # Strip " FOR ..." suffix: "TOMATOES FOR PROCESSING" → "TOMATOES"
    name = re.sub(r'\s+FOR\s+.*$', '', name).strip()
    # Strip parentheticals: "WALNUTS (ENGLISH)" → "WALNUTS"
    name = re.sub(r'\s*\(.*?\)', '', name).strip()
    # Strip "ALL " prefix: "ALL GRAPES" → "GRAPES"
    name = re.sub(r'^ALL\s+', '', name).strip()
    return name


def get_api_name(database_name: str) -> Optional[str]:
    """
    Get the QuickStats commodity_desc for a NASS commodity code name.

    Checks OFFICIAL_API_MAPPINGS first (explicit reviewed entries), then falls
    back to guess_api_name() heuristic.

    Returns:
        str   — the API name to use in QuickStats queries
        None  — entry is in DISABLED_API_MAPPINGS; caller should leave
                api_name NULL in the database and skip API queries
    """
    if database_name in DISABLED_API_MAPPINGS:
        return None
    if database_name in OFFICIAL_API_MAPPINGS:
        return OFFICIAL_API_MAPPINGS[database_name]
    return guess_api_name(database_name)


def get_all_api_names() -> list[str]:
    """Get all unique API names that we use for API requests (from reviewed mappings only)."""
    return list(set(OFFICIAL_API_MAPPINGS.values()))


# ============================================================================
# Draft builder
#
# Run as:  python reviewed_api_mappings.py [--api-key KEY] [--output FILE]
#
# Scrapes the full ~400 NASS commodity list, applies heuristic guesses, and
# optionally validates each guess against the live QuickStats commodity_desc
# list.  Prints a reviewable table and a copy-pasteable dict block.
# ============================================================================

if __name__ == '__main__':
    import sys
    import json
    import argparse
    import os
    import requests
    from pathlib import Path
    from datetime import datetime

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print('ERROR: beautifulsoup4 is required.  Run: pip install beautifulsoup4')
        sys.exit(1)

    # Load .env from repo root (walk up until pixi.toml is found)
    _repo_root = next(
        (p for p in Path(__file__).resolve().parents if (p / 'pixi.toml').exists()),
        Path(__file__).resolve().parent
    )
    _env_file = _repo_root / '.env'
    if _env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_env_file)
        except ImportError:
            # Manual parse fallback if python-dotenv not available
            for line in _env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())

    def _scrape_nass_codes() -> list:
        """Scrape all commodity codes from commcodes.php."""
        url = ('https://www.nass.usda.gov/Data_and_Statistics/County_Data_Files/'
               'Frequently_Asked_Questions/commcodes.php')
        print(f'Scraping {url} ...')
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table')
        if not table:
            raise RuntimeError('No table found on commcodes.php')
        rows = table.find_all('tr')
        hdrs = [c.get_text().strip().lower() for c in rows[0].find_all(['th', 'td'])]
        code_col = next((i for i, h in enumerate(hdrs) if h == 'cmdty' or 'code' in h), None)
        desc_col = next((i for i, h in enumerate(hdrs) if 'desc' in h), None)
        if code_col is None or desc_col is None:
            raise RuntimeError(f'Could not identify columns in: {hdrs}')
        out = []
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= max(code_col, desc_col):
                continue
            code = cells[code_col].get_text().strip()
            name = cells[desc_col].get_text().strip().upper()
            if code and name and len(code) >= 4:
                out.append({'code': code, 'name': name})
        print(f'  -> {len(out)} commodities scraped')
        return out

    def _fetch_quickstats_names(api_key: str) -> set:
        """Fetch all valid commodity_desc values from the QuickStats get_param_values endpoint."""
        print('Fetching QuickStats commodity_desc list...')
        url = 'https://quickstats.nass.usda.gov/api/get_param_values/'
        r = requests.get(url, params={'key': api_key, 'param': 'commodity_desc'}, timeout=60)
        r.raise_for_status()
        names = set(r.json().get('commodity_desc', []))
        print(f'  -> {len(names)} commodity_desc values in QuickStats API')
        return names

    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description='Build a complete draft of OFFICIAL_API_MAPPINGS from live USDA sources.'
    )
    parser.add_argument('--api-key', metavar='KEY',
                        help='USDA NASS API key (overrides USDA_NASS_API_KEY from .env)')
    parser.add_argument('--output', metavar='FILE',
                        help='Write the copy-paste block to this file instead of stdout')
    parser.add_argument('--list-quickstats', metavar='FILE', nargs='?', const='-',
                        help='Fetch and print/write all QuickStats commodity_desc values, then exit. '
                             'Pass a filename to write to a file, or omit for stdout.')
    args = parser.parse_args()

    api_key = args.api_key or os.getenv('USDA_NASS_API_KEY')

    # --list-quickstats: just dump the commodity_desc list and exit
    if args.list_quickstats is not None:
        if not api_key:
            print('ERROR: --list-quickstats requires an API key.')
            print('       Set USDA_NASS_API_KEY in .env or pass --api-key KEY')
            raise SystemExit(1)
        qs_names = _fetch_quickstats_names(api_key)
        lines = [f'# QuickStats commodity_desc values ({len(qs_names)} total)\n']
        lines += [f'{name}\n' for name in sorted(qs_names)]
        dest = args.list_quickstats
        if dest == '-':
            print(''.join(lines), end='')
        else:
            Path(dest).write_text(''.join(lines), encoding='utf-8')
            print(f'[OK] {len(qs_names)} QuickStats names written to {dest}')
        raise SystemExit(0)

    if not api_key:
        print('WARNING: No USDA_NASS_API_KEY found in .env or --api-key flag.')
        print('         Proceeding without QuickStats validation (guesses flagged <- VALIDATE)')

    # Step 1: get full NASS list
    nass_commodities = _scrape_nass_codes()

    # Step 2: optionally get QuickStats valid names
    qs_names: set = set()
    if api_key:
        qs_names = _fetch_quickstats_names(api_key)
    else:
        print('  (skipping QuickStats validation; guesses flagged <- VALIDATE)')

    # Step 3: classify
    already_official = set(OFFICIAL_API_MAPPINGS.keys())
    already_disabled = set(DISABLED_API_MAPPINGS.keys())
    new_entries = [
        c for c in nass_commodities
        if c['name'] not in already_official and c['name'] not in already_disabled
    ]

    print(f"\n{'=' * 80}")
    print('DRAFT SUMMARY')
    print(f"{'=' * 80}")
    print(f'  Total NASS commodities scraped   : {len(nass_commodities)}')
    print(f'  Already in OFFICIAL_API_MAPPINGS : {len(already_official)}')
    print(f'  Already in DISABLED_API_MAPPINGS : {len(already_disabled)}')
    print(f'  New entries to review            : {len(new_entries)}')

    official_draft: list = []  # (nass_name, api_name, flag)
    disabled_draft: list = []  # (nass_name, reason)

    for c in new_entries:
        name = c['name']
        guessed = guess_api_name(name)
        if qs_names:
            if guessed in qs_names:
                official_draft.append((name, guessed, 'auto-matched'))
            else:
                # Guess not found — move to disabled with explanation
                disabled_draft.append((name, guessed,
                                       f"guess '{guessed}' not in QuickStats list"))
        else:
            # No API key — classify by whether name changed
            changed = guessed != name
            flag = '<- VALIDATE' if changed else 'auto-matched (unvalidated)'
            official_draft.append((name, guessed, flag))

    # Review table
    if official_draft:
        print(f"\n{'=' * 90}")
        print(f'OFFICIAL DRAFT  ({len(official_draft)} entries)  — add to OFFICIAL_API_MAPPINGS')
        print(f"{'=' * 90}")
        print(f"  {'NASS Code Name':<45} {'-> API Name':<35} Note")
        print(f"  {'-' * 44} {'-' * 34} {'-' * 20}")
        for name, api, note in sorted(official_draft):
            marker = ' *' if api != name else ''
            print(f'  {name[:44]:<45} {api[:34]:<35} {note}{marker}')

    if disabled_draft:
        print(f"\n{'=' * 90}")
        print(f'DISABLED DRAFT  ({len(disabled_draft)} entries)  — add to DISABLED_API_MAPPINGS')
        print(f'  Heuristic guess not found in QuickStats API list.')
        print(f'  Review each: correct the guess and move to OFFICIAL, or leave in DISABLED.')
        print(f"{'=' * 90}")
        for name, guessed, reason in sorted(disabled_draft):
            print(f"  {name[:44]:<45}  # {reason}")

    # Copy-paste block
    lines = []
    today = datetime.now().strftime('%Y-%m-%d')
    sep72 = '=' * 72
    if official_draft:
        lines.append('')
        lines.append(f'# {sep72}')
        lines.append(f'# OFFICIAL_API_MAPPINGS additions  —  generated {today}')
        lines.append(f'# Review lines marked <- VALIDATE before committing')
        lines.append(f'# {sep72}')
        for name, api, note in sorted(official_draft):
            validate = '  # <- VALIDATE' if '<- VALIDATE' in note else ''
            lines.append(f"    {name!r}: {api!r},{validate}")

    if disabled_draft:
        lines.append('')
        lines.append(f'# {sep72}')
        lines.append(f'# DISABLED_API_MAPPINGS additions  —  generated {today}')
        lines.append('# These were NOT found in the QuickStats API commodity list.')
        lines.append('# For each entry either:')
        lines.append('#   (a) find the correct QuickStats name, change the value, and move the')
        lines.append('#       line to OFFICIAL_API_MAPPINGS above, OR')
        lines.append('#   (b) leave it here — api_name will remain NULL in the database.')
        lines.append(f'# {sep72}')
        for name, guessed, reason in sorted(disabled_draft):
            same = guessed == name
            hint = '  # heuristic unchanged — find the correct QuickStats name' if same else f'  # heuristic guess: {guessed!r} — verify before moving to OFFICIAL'
            lines.append(f"    {name!r}: 'not in QuickStats API list',{hint}")

    # Append full QuickStats reference list if we fetched it
    qs_ref_lines = []
    if qs_names:
        qs_ref_lines.append('')
        qs_ref_lines.append('# ' + '=' * 72)
        qs_ref_lines.append(f'# QUICKSTATS REFERENCE  —  all {len(qs_names)} valid commodity_desc values')
        qs_ref_lines.append('# Ctrl+F this section to find the correct right-hand value for DISABLED entries.')
        qs_ref_lines.append('# Copy the exact string (case-sensitive) into OFFICIAL_API_MAPPINGS.')
        qs_ref_lines.append('# ' + '=' * 72)
        for qs_name in sorted(qs_names):
            qs_ref_lines.append(f'#   {qs_name}')

    output_text = '\n'.join(lines + qs_ref_lines)
    if args.output:
        Path(args.output).write_text(output_text + '\n', encoding='utf-8')
        print(f'\n[OK] Draft written to {args.output}')
        if qs_ref_lines:
            print(f'     Includes full QuickStats reference list ({len(qs_names)} entries) at the bottom.')
    else:
        print(f"\n{'=' * 80}")
        print('COPY-PASTE BLOCK  (paste into reviewed_api_mappings.py and edit)')
        print(f"{'=' * 80}")
        print(output_text)

"""
# QuickStats commodity_desc values (467 total)
AG LAND
AG SERVICES
AG SERVICES & RENT
ALCOHOL COPRODUCTS
ALMONDS
ALPACAS
AMARANTH
ANIMAL PRODUCTS, OTHER
ANIMAL SECTOR
ANIMAL TOTALS
ANIMALS, OTHER
ANNUAL PPI
APPLES
APRICOTS
AQUACULTURE TOTALS
AQUACULTURE, OTHER
AQUATIC PLANTS
ARONIA BERRIES
ARTICHOKES
ASPARAGUS
ASSETS
AUTOMOBILES
AUTOS
AVOCADOS
BAITFISH
BANANAS
BAREROOT HERBACEOUS PERENNIALS
BARLEY
BASIL
BEANS
BEDDING PLANT TOTALS
BEDDING PLANTS, ANNUAL
BEDDING PLANTS, HERBACEOUS PERENNIAL
BEEF
BEESWAX
BEETS
BERRIES, OTHER
BERRY TOTALS
BETEL NUTS
BISON
BITTERMELON
BLACKBERRIES
BLUEBERRIES
BOATS
BOYSENBERRIES
BREADFRUIT
BROCCOLI
BRUSSELS SPROUTS
BUCKWHEAT
BUILDING MATERIALS
BUILDINGS
BULBS & CORMS & RHIZOMES & TUBERS
BULBS & ROOTS
BUSINESS ACTIVITY
BUTTER
BUTTERMILK
CABBAGE
CACAO
CACTI & SUCCULENTS
CAKE & MEAL
CAMELINA
CANEBERRIES
CANOLA
CARABAO
CARROTS
CASH RECEIPT TOTALS
CASSAVA
CATTLE
CAULIFLOWER
CCC LOANS
CELERY
CHAIN SAWS
CHEESE
CHEMICAL TOTALS
CHEMICALS, OTHER
CHERIMOYAS
CHERRIES
CHESTNUTS
CHICKENS
CHICKPEAS
CHICORY
CHIRONJAS
CHIVES
CHUKARS
CILANTRO
CITRONS
CITRUS TOTALS
CITRUS, OTHER
COCONUTS
COFFEE
COFFEE DEPULPERS
COFFEE DRYERS
COFFEE WASHERS
COLD STORAGE CAPACITY
COMMODITY TOTALS
COMPUTERS
CONSUMER PRICE INDEX
CORIANDER
CORN
COTTON
CRAMBE
CRANBERRIES
CREAM
CROP SECTOR
CROP TOTALS
CROPS, OTHER
CRUDE PINE GUM
CRUSTACEANS
CUCUMBERS
CURRANTS
CUT CHRISTMAS TREES
CUT CHRISTMAS TREES & SHORT TERM WOODY TREES
CUT CULTIVATED GREENS
CUT FLOWERS
CUT FLOWERS & CUT CULTIVATED GREENS
DAIKON
DAIRY PRODUCT TOTALS
DAIRY PRODUCTS, OTHER
DASHEENS
DATES
DEBT
DECIDUOUS FLOWERING TREES
DECIDUOUS SHADE TREES
DECIDUOUS SHRUBS
DEER
DEPRECIATION
DILL
DRAGON FRUIT
DUCKS
EGGPLANT
EGGS
ELDERBERRIES
ELECTRICITY
ELK
EMERGENCY ELECTRIC GENERATORS
EMMER & SPELT
EMUS
ENERGY
EQUINE
EQUIPMENT, OTHER
ESCAROLE & ENDIVE
EVERGREENS, BROADLEAF
EVERGREENS, CONIFEROUS
EXPENSE TOTALS
EXPENSES, OTHER
FACILITIES & EQUIPMENT
FARM BY-PRODUCTS & WASTE
FARM OPERATIONS
FARM SECTOR
FEED
FEED GRAINS
FEED GRAINS & HAY
FEED PRICE RATIO
FERTILIZER
FERTILIZER & CHEMICAL TOTALS
FERTILIZER TOTALS
FERTILIZER, MIXED
FERTILIZER, OTHER
FIELD CROP & VEGETABLE TOTALS
FIELD CROP TOTALS
FIELD CROPS & VEGETABLES, OTHER
FIELD CROPS, OTHER
FIELDWORK
FIGS
FISH
FISH & GIANT CLAMS
FLAXSEED
FLORICULTURE TOTALS
FLORICULTURE, OTHER
FLOUR
FLOWER SEEDS
FLOWERING PLANTS, POTTED
FOLIAGE PLANTS
FOOD COMMODITIES
FOOD CROP TOTALS
FOOD CROP, OTHER
FOOD FISH
FOOD GRAINS
FRUIT & NUT PLANTS
FRUIT & TREE NUT TOTALS
FRUIT & TREE NUTS, OTHER
FRUIT BEARING TREES
FRUIT TOTALS
FRUIT, OTHER
FUELS
FUMIGANTS
FUNGICIDES
FUNGICIDES & OTHER
GADO
GARLIC
GEESE
GINGER ROOT
GINSENG
GOATS
GOOSEBERRIES
GOURDS
GOVT PROGRAM TOTALS
GOVT PROGRAMS
GRAIN
GRAIN STORAGE CAPACITY
GRAPEFRUIT
GRAPES
GRASSES
GRASSES & LEGUMES TOTALS
GRASSES & LEGUMES, OTHER
GREASE
GREENS
GROWING MEDIA
GUAR
GUAVAS
GUINEAS
HAY
HAY & HAYLAGE
HAYLAGE
HAZELNUTS
HEMP
HERBICIDES
HERBS
HERBS & SPICES
HOGS
HONEY
HOPS
HORSERADISH
HORTICULTURE TOTALS
HORTICULTURE, OTHER
ICE CREAM
IMPROVEMENT & CONSTRUCTION
INCOME, FARM-RELATED
INCOME, NET CASH FARM
INSECTICIDES
INTEREST
INTERNET
IRRIGATION ORGANIZATIONS
JICAMA
JOJOBA
K-EARLY CITRUS
KAVA
KIWIFRUIT
KUMQUATS
LABOR
LAMB & MUTTON
LAND AREA
LANDLORDS
LARD
LAUPELE
LEGUMES
LEMONS
LEMONS & LIMES
LENTILS
LETTUCE
LIMES
LIVESTOCK TOTALS
LIVESTOCK, OTHER
LLAMAS
LOGANBERRIES
LONGAN
LOTUS ROOT
LYCHEES
MACADAMIAS
MACHINERY
MACHINERY TOTALS
MACHINERY, OTHER
MANGOES
MAPLE SYRUP
MEAL
MEDICINE & DRUGS
MELLORINE
MELONS
MICROGREENS
MILK
MILK COOLERS
MILKING MACHINES
MILLET
MILLFEED
MINK
MINT
MISCANTHUS
MOHAIR
MOLLUSKS
MOUNTAIN APPLES
MULBERRIES
MUSHROOM SPAWN
MUSHROOMS
MUSTARD
NECTARINES
NITROGEN
NON-CITRUS FRUIT & TREE NUTS TOTALS
NON-CITRUS TOTALS
NON-CITRUS, OTHER
NONFARM SECTOR
NURSERY & FLORICULTURE TOTALS
NURSERY TOTALS
NURSERY, OTHER
OATS
OIL
OIL-BEARING CROPS
OKRA
OLIVES
ONIONS
OPERATORS
OPERATORS, FIRST FOUR OPERATORS
OPERATORS, PRINCIPAL
OPERATORS, SECOND
OPERATORS, THIRD
ORANGES
ORCHARDS
ORNAMENTAL FISH
ORNAMENTAL GRASSES
ORNAMENTAL TREE SEEDLINGS
OSTRICHES
PACKING FACILITY
PALMS
PAPAYAS
PARSLEY
PARSNIPS
PARTRIDGES
PASSION FRUIT
PASTURELAND
PAWPAWS
PEACHES
PEACHES & NECTARINES
PEAFOWL
PEANUTS
PEARS
PEAS
PEAS & CARROTS
PEAS & LENTILS
PECANS
PEPPERS
PERSIMMONS
PHEASANTS
PHOSPHATE
PICKLES
PIGEONS & SQUAB
PIMIENTOS
PINEAPPLES
PISTACHIOS
PITW
PLANTAINS
PLUM-APRICOT HYBRIDS
PLUMS
PLUMS & PRUNES
POINSETTIAS
POMEGRANATES
POPCORN
PORK
POTASH
POTASH & PHOSPHATE
POTATOES
POTATOES & DRY BEANS
POULTRY BY-PRODUCT MEALS
POULTRY FATS
POULTRY TOTALS
POULTRY, OTHER
PPITW
PRACTICES
PRICE INDEX RATIO
PRODUCERS
PRODUCERS, (EXCL PRINCIPAL)
PRODUCERS, FIRST FOUR PRODUCERS
PRODUCERS, PRIMARY
PRODUCERS, PRINCIPAL
PRODUCTION ITEMS
PRODUCTION ITEMS & CONSUMER PRICE INDEX
PROPAGATIVE MATERIAL
PROPAGATIVE MATERIALS TOTALS
PRUNES
PUMPKINS
PUMPS
QUAIL
QUENEPAS
RABBITS
RADISHES
RAMBUTAN
RAPESEED
RASPBERRIES
RED MEAT
RENT
REPAIRS
RETURNS & ALLOWANCES
RHEAS
RHUBARB
RICE
ROOT CELERY
ROOT CROPS & TUBERS
ROOT CROPS & TUBERS, OTHER
ROOTS & TUBERS
ROOTS, OTHER
ROW CROPS
RYE
SAFFLOWER
SEEDS
SEEDS & PLANTS TOTALS
SELF PROPELLED
SESAME
SHEEP
SHEEP & GOATS TOTALS
SHERBET
SHORT TERM WOODY TREES
SILAGE
SMALL GRAINS
SNOW
SOD
SOIL
SORGHUM
SORREL
SOURSOPS
SOYBEANS
SPECIALTY ANIMAL TOTALS
SPECIALTY ANIMALS, OTHER
SPINACH
SPORT FISH
SPRAYERS
SPROUTS
SQUASH
STARFRUIT
STRAWBERRIES
STRING TRIMMERS
SUGARBEETS
SUGARCANE
SUNFLOWER
SUPPLIES
SUPPLIES & REPAIRS
SWEET CORN
SWEET POTATOES
SWEET RICE
SWEETSOPS
SWITCHGRASS
TALLOW
TANGELOS
TANGERINES
TANIERS
TARO
TAXES
TEMPLES
TENANTS
TILLERS
TOBACCO
TOMATOES
TRACTORS
TRACTORS & SELF PROPELLED
TRANSPLANTS
TREE NUT TOTALS
TREE NUTS, OTHER
TRITICALE
TRUCKS
TRUCKS & AUTOS
TURKEYS
TURNIPS
VEAL
VEGETABLE SEEDS
VEGETABLE TOTALS
VEGETABLES, MIXED
VEGETABLES, OTHER
WALNUTS
WATER
WATER ICES
WATERCRESS
WELLS
WHEAT
WHEY
WILD RICE
WOOD CHIPPERS
WOODY ORNAMENTALS & VINES, OTHER
WOOL
YAMS
YOGURT

"""
