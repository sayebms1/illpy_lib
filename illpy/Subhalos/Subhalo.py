"""
Submodule to import particle data from illustris snapshots.  Wrappers for `illustris_python`.

Functions
---------
   importSubhaloParticles : import snapshot data for a given subhalo
   importGroupCatalogData : import group catalog data for subhalo(s)

"""

from datetime import datetime
import numpy as np

import illpy
from illpy.Constants import GET_ILLUSTRIS_OUTPUT_DIR, PARTICLE
from Constants import SUBHALO

VERBOSE = True

LOAD_PARTICLES = [PARTICLE.GAS, PARTICLE.DM, PARTICLE.STAR, PARTICLE.BH]


def importSubhaloParticles(run, snapNum, subhalo, partTypes=None, verbose=VERBOSE):
    """
    Import particle data for a given Subhalo from the illustris snapshot files.

    The target particle types are the standard, e.g. 0-gas, 1-dm, etc described by the constants in
    ``illpy.Constants.PARTICLE``.  Each particle type has a different set of parameters returned in
    the resulting dictionaries in the ``data`` output.

    Arguments
    ---------
       run       <int>      : Illustris simulation number {1, 3}
       snapNum   <int>      : Illustris snapshot number {1, 135}
       subhalo   <int>      : Subhalo index for this snapshot
       partTypes <int>([N]) : optional, Target particle types; if `None`, all are loaded
       verbose   <bool>     : optional, print verbose output

    Returns
    -------
       data      <dict>([N]) : dictionary of target particle data
                               If a single ``partType`` is given, a single dictionary is returned.
                               Otherwise a list of dictionaries, one for each ``partType`` is
                               returned in the same order as provided.

       partTypes <int>([N])  : Particle number for returned data, same ordering as ``data``.


    Additional Parameters
    ---------------------
       LOAD_PARTICLES <int>[N] : Default list of particle types to load if ``partType == None``.

    """

    import illustris_python as ill

    if(verbose): print " - - Subhalos._importSubhaloParticles()"

    # Prepare Particle Types to Import
    #  --------------------------------
    # Set particle types to Default
    if(partTypes is None): partTypes = LOAD_PARTICLES

    # Make sure ``partTypes`` is iterable
    if(not np.iterable(partTypes)): partTypes = [partTypes]

    # Get names of particle types
    partNames = [PARTICLE.NAMES(ptype) for ptype in partTypes]

    # Get snapshot file path and filename
    outputPath = GET_ILLUSTRIS_OUTPUT_DIR(run)

    # Load Snapshot data for target Particles
    #  ---------------------------------------
    if(verbose): print " - - - Loading snapshot data"
    data = []
    if(verbose): start_all = datetime.now()
    # Iterate over particle types
    for ptype, pname in zip(partTypes, partNames):
        if(verbose): start = datetime.now()
        partData = ill.snapshot.loadSubhalo(outputPath, snapNum, subhalo, ptype)
        data.append(partData)
        if(verbose): stop = datetime.now()
        numParts = partData['count']
        numParams = len(partData.keys())-1
        if(verbose):
            print "         %8d %6s, %2d pars, after %s" % \
                (numParts, pname, numParams, str(stop-start))

    if(verbose): stop_all = datetime.now()
    if(verbose): print " - - - - All After %s" % (str(stop_all-start_all))

    # If single particle, don't both with list
    if(len(data) == 1): data = data[0]

    return data, partTypes


def importGroupCatalogData(run, snapNum, subhalos=None, fields=None, verbose=VERBOSE):
    """
    Load group catalog data for all or some subhalos.

    Arguments
    ---------
       run      <int>      : illustris simulation run number {1, 3}
       snapNum  <int>      : illustris snapshot number {1, 135}
       subhalos <int>([N]) : target subhalo numbers
       fields   <str>([M]) : target catalog parameters
       verbose  <bool>     : print verbose output

    Returns
    -------
       subcat   <dict>     : dictionary of catalog properties (see ``illpy.Constants.SUBHALO``)

    """

    import illustris_python as ill

    if verbose: print " - - Subhalo.importGroupCatalogData()"

    # If no group-catalog fields given, use all of them (available)
    if fields is None: fields = SUBHALO.PROPERTIES()

    # Load Group Catalog
    # ------------------
    path_output = GET_ILLUSTRIS_OUTPUT_DIR(run)
    if verbose: print " - - - Loading group catalog from '%s'" % (path_output)
    try:
        gcat = ill.groupcat.loadSubhalos(path_output, snapNum, fields=fields)
    except:
        print("\n\nFailed at snapNum = '{}'\n\tpath = '{}'\n\tfields = '{}'".format(
            snapNum, path_output, fields))
        raise

    if isinstance(gcat, dict): numSubhalos = gcat['count']
    else:                      numSubhalos = len(gcat)
    if verbose: print " - - - - Loaded %d subhalos" % (numSubhalos)

    # If no subhalos selected, return full catalog
    if subhalos is None: return gcat

    # Extract Target Subhalos
    # -----------------------
    if isinstance(gcat, dict):
        subcat = {}
        for key in gcat.keys():
            if(key is not 'count'): subcat[key] = gcat[key][subhalos]
    else:
        subcat = gcat[subhalos]

    return subcat
