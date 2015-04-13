"""
Module to handle Illustris blackhole details files.

Details are accessed via 'intermediate' files which are reorganized versions of the 'raw' illustris
files 'blackhole_details_<#>.txt'.  The `main()` function assures that details entries are properly
converted from raw to processed form, organized by time of entry instead of processor.  Those
details can then be accessed by snapshot and blackhole ID number.

Functions
---------
main() : returns None, assures that intermediate files exist -- creating them if necessary.
detailsForBH() : returns dict, dict; retrieves the details entries for a given BH ID number.


Notes
-----
  - The BH Details files from illustris, 'blackhole_details_<#>.txt' are organized by the processor
    on which each BH existed in the simulation.  The method `_reorganizeBHDetails()` sorts each
    detail entry instead by the time (scalefactor) of the entry --- organizing them into files
    grouped by which snapshot interval the detail entry corresponds to.  The reorganization is
    first done into 'temporary' ASCII files before being converted into numpy `npz` files by the
    method `_convertDetailsASCIItoNPZ()`.  The `npz` files are effectively dictionaries storing
    the select details parameters (i.e. mass, BH ID, mdot, rho, cs), along with some meta data
    about the `run` number, and creation time, etc.  Execution of the BHDetails ``main`` routine
    checks to see if the npz files exist, and if they do not, they are created.

  - There are also routines to obtain the details entries for a specific BH ID.  In particular,
    the method `detailsForBH()` will return the details entry/entries for a target BH ID and
    run/snapshot.

  - Illustris Blackhole Details Files 'blackhole_details_<#>.txt'
    - Each entry is given as
      0   1            2     3     4    5
      ID  scalefactor  mass  mdot  rho  cs


"""

### Builtin Modules ###
import os, sys
from glob import glob

import numpy as np
from datetime import datetime

from BHConstants import *
from .. import AuxFuncs as aux


VERSION = 0.23                                                                                      # Version of BHDetails

_DEF_PRECISION = -8                                                                                 # Default precision




def processDetails(run, loadsave=True, verbose=VERBOSE):

    if( verbose ): print " - - BHDetails.processDetails()"

    # Organize Details by Snapshot Time; create new, temporary ASCII Files
    tempFiles = organizeDetails(run, loadsave=loadsave, verbose=verbose)

    # Create Dictionary Details Files
    saveFiles = formatDetails(run, loadsave=loadsave, verbose=verbose)

    return

# processDetails()




def organizeDetails(run, loadsave=True, verbose=VERBOSE):

    if( verbose ): print " - - BHDetails.organizeDetails()"

    tempFiles = [ GET_DETAILS_TEMP_FILENAME(run, snap) for snap in xrange(NUM_SNAPS) ]

    # Check if all temp files already exist
    if( loadsave ):
        tempExist = aux.filesExist(tempFiles)
        if( not tempExist ):
            if( verbose ): print " - - - Temp files do not exist '%s'" % (tempFiles[0])
            loadsave = False


    # If temp files dont exist, or we WANT to redo them, then create temp files
    if( not loadsave ):

        # Get Illustris BH Details Filenames
        if( verbose ): print " - - - Finding Illustris BH Details files"
        rawFiles = GET_ILLUSTRIS_BH_DETAILS_FILENAMES(run, verbose)
        if( len(rawFiles) < 1 ): raise RuntimeError("Error no details files found!!")

        # Reorganize into temp files
        if( verbose ): print " - - - Reorganizing details into temporary files"
        _reorganizeBHDetailsFiles(run, rawFiles, tempFiles, verbose=verbose)


    # Confirm all temp files exist
    tempExist = aux.filesExist(tempFiles)

    # If files are missing, raise error
    if( tempExist ):
        if( verbose ): print " - - - Temp files exist"
    else:
        print "Temporary Files still missing!  '%s'" % (tempFiles[0])
        raise RuntimeError("Temporary Files missing!")


    return tempFiles

# organizeDetails()



def formatDetails(run, loadsave=True, verbose=VERBOSE):

    if( verbose ): print " - - BHDetails.formatDetails()"

    # See if all npz files already exist
    saveFilenames = [ GET_DETAILS_SAVE_FILENAME(run, snap, VERSION) for snap in xrange(NUM_SNAPS) ]

    # Check if all save files already exist, and correct versions
    if( loadsave ):
        saveExist = aux.filesExist(saveFilenames)
        if( saveExist ):
            dets = loadBHDetails(run, 0)
            loadVers = dets[DETAILS_VERSION]
            if( loadVers != VERSION ):
                print "BHDetails.formatDetails() : loaded version %s from '%s'" % (str(loadVers), dets[DETAILS_FILE])
                print "BHDetails.formatDetails() : current version %s" % (str(VERSION))
                print "BHDetails.formatDetails() : re-converting Details files !!!"
                loadsave = False

        else:
            print "BHDetails.formatDetails() : Save files do not exist e.g. '%s'" % (saveFilenames[0])
            print "BHDetails.formatDetails() : converting raw Details files !!!"
            loadsave = False


    if( not loadsave ):

        if( verbose ): print " - - - Converting temporary files to NPZ"
        _convertDetailsASCIItoNPZ(run, verbose=verbose)


    # Confirm save files exist
    saveExist = aux.filesExist(saveFilenames)

    # If files are missing, raise error
    if( saveExist ):
        if( verbose ): print " - - - Save files exist."
    if( not saveExist ):
        print "Save Files missing!  e.g. '%s'" % (saveFilenames[0])
        raise RuntimeError("Save Files missing!")


    return saveFilenames

# formatDetails()



def _reorganizeBHDetailsFiles(run, rawFilenames, tempFilenames, verbose=VERBOSE):

    if( verbose ): print " - - BHDetails._reorganizeBHDetailsFiles()"

    # Load cosmology
    from illpy import illcosmo
    cosmo = illcosmo.Cosmology()
    snapScales = cosmo.snapshotTimes()


    # Open new ASCII, Temp details files
    #    Make sure path is okay
    aux.checkPath(tempFilenames[0])
    # Open each temp file
    tempFiles = [ open(tfil, 'w') for tfil in tempFilenames ]

    numTemp = len(tempFiles)
    numRaw  = len(rawFilenames)
    if( verbose ): print " - - - Organizing %d raw files into %d temp files" % (numRaw, numTemp)


    ### Iterate over all Illustris Details Files ###

    if( verbose ): print " - - - Sorting details into times of snapshots"
    start = datetime.now()
    for ii,rawName in enumerate(rawFilenames):

        detLines = []
        detScales = []
        # Load all lines and entry scale-factors from raw details file
        for dline in open(rawName):
            detLines.append(dline)
            # Extract scale-factor from line
            detScale = DBL( dline.split()[1] )
            detScales.append(detScale)


        # Convert to array
        detLines  = np.array(detLines)
        detScales = np.array(detScales)

        # If file is empty, continue
        if( len(detLines) <= 0 or len(detScales) <= 0 ): continue

        # Get required precision in matching entry times (scales)
        try:
            prec = _getPrecision(detScales)
        # Set to a default value on error (not sure what's causing it)
        except ValueError, err:
            print "BHDetails._reorganizeBHDetailsFiles() : caught error '%s'" % (str(err))
            print "\tii = %d; file = '%s'" % (ii, rawName)
            print "\tlen(detScales) = ", len(detScales)
            prec = _DEF_PRECISION


        # Round snapshot scales to desired precision
        roundScales = np.around(snapScales, -prec)

        # Find snapshots following each entry (right-edge) or equal (include right: 'right=True')
        snapBins = np.digitize(detScales, roundScales, right=True)

        # For each Snapshot, write appropriate lines
        for jj in xrange(len(tempFiles)):

            inds = np.where( snapBins == jj )[0]
            if( len(inds) > 0 ):
                tempFiles[jj].writelines( detLines[inds] )

        # } jj



        # Print Progress
        if( verbose ):
            # Find out current duration
            now = datetime.now()
            dur = now-start

            # Print status and time to completion
            statStr = aux.statusString(ii+1, numRaw, dur)
            sys.stdout.write('\r - - - - %s' % (statStr))
            sys.stdout.flush()

        # } verbose

    # } ii

    if( verbose ): sys.stdout.write('\n')

    # Close out details files.
    fileSizes = 0.0
    for ii, newdf in enumerate(tempFiles):
        newdf.close()
        fileSizes += os.path.getsize(newdf.name)

    if( verbose ):
        aveSize = fileSizes/(1.0*len(tempFiles))
        sizeStr = aux.bytesString(fileSizes)
        aveSizeStr = aux.bytesString(aveSize)
        print " - - - Total temp size = '%s', average = '%s'" % (sizeStr, aveSizeStr)


    inLines = aux.countLines(rawFilenames, progress=True)
    outLines = aux.countLines(tempFilenames, progress=True)
    if( verbose ): print " - - - Input lines = %d, Output lines = %d" % (inLines, outLines)
    if( inLines != outLines ):
        print "in  file: ", rawFilenames[0]
        print "out file: ", tempFilenames[0]
        raise RuntimeError("WARNING: input lines = %d, output lines = %d!" % (inLines, outLines))


    return



def _convertDetailsASCIItoNPZ(run, verbose=VERBOSE):
    """
    Convert all snapshot ASCII details files to dictionaries in NPZ files.
    """

    if( verbose ): print " - - BHDetails._convertDetailsASCIItoNPZ()"

    start = datetime.now()
    filesSize = 0.0
    sav = None

    ### Iterate over all Snapshots, convert from ASCII to NPZ ###

    # Go through snapshots in random order to make better estimate of duration
    allSnaps = np.arange(NUM_SNAPS)
    np.random.shuffle(allSnaps)

    for ii,snap in enumerate(allSnaps):

        # Convert this particular snapshot
        saveFilename = _convertDetailsASCIItoNPZ_snapshot(run, snap, verbose=False)

        # Find and report progress
        if( verbose ):
            filesSize += os.path.getsize(saveFilename)

            now = datetime.now()
            dur = now-start

            statStr = aux.statusString(ii+1, NUM_SNAPS, dur)
            sys.stdout.write('\r - - - %s' % (statStr))
            sys.stdout.flush()
            if( ii+1 == NUM_SNAPS ): sys.stdout.write('\n')

    # } snap


    if( verbose ):
        aveFileSize = filesSize / NUM_SNAPS
        totSize = aux.bytesString(filesSize)
        aveSize = aux.bytesString(aveFileSize)
        print " - - - Saved Details NPZ files.  Total size = %s, Ave Size = %s" % \
            (totSize, aveSize)


    return



def _convertDetailsASCIItoNPZ_snapshot(run, snap, loadsave=True, verbose=VERBOSE):
    """
    Convert a single snapshot ASCII Details file to dictionary saved to NPZ file.

    Makes sure the ASCII file exists, if not, ASCII 'temp' files are reloaded
    for all snapshots from the 'raw' details data from illustris.

    Arguments
    ---------

    Returns
    -------

    """

    if( verbose ): print " - - BHDetails._convertDetailsASCIItoNPZ_snapshot()"

    tmp = GET_DETAILS_TEMP_FILENAME(run, snap)
    sav = GET_DETAILS_SAVE_FILENAME(run, snap, VERSION)

    ### Make Sure Temporary Files exist, Otherwise re-create them ###
    if( not os.path.exists(tmp) ):
        print "BHDetails._convertDetailsASCIItoNPZ_snapshot(): no temp file '%s' " % (tmp)
        print "BHDetails._convertDetailsASCIItoNPZ_snapshot(): Reloading all temp files!!"
        tempFiles = organizeDetails(run, loadsave=loadsave, verbose=verbose)


    ### Try to load from existing save ###
    if( loadsave ):
        
        if( os.path.exists(sav) ):
            details = aux.npzToDict(sav)
            loadVers = details[DETAILS_VERSION]
            if( loadVers != VERSION ):
                loadsave = False
                if( verbose ): 
                    print " - - - Loaded  v%s" % (str(loadVers))
                    print " - - - Current v%s" % (str(VERSION ))

        else:
            if( verbose ): print " - - - File does not exist"
            loadsave = False
                


    ### Load Details from ASCII, Convert to Dictionary and Save to NPZ ###
                
    if( not loadsave ):

        # Load details from ASCII File
        ids, scales, masses, mdots, rhos, cs = _loadBHDetails_ASCII(tmp)

        # Store details in dictionary
        details = { DETAILS_NUM     : len(ids),
                    DETAILS_RUN     : run,
                    DETAILS_SNAP    : snap,
                    DETAILS_CREATED : datetime.now().ctime(),
                    DETAILS_VERSION : VERSION,
                    DETAILS_FILE    : sav,

                    DETAILS_IDS     : ids,
                    DETAILS_SCALES  : scales,
                    DETAILS_MASSES  : masses,
                    DETAILS_MDOTS   : mdots,
                    DETAILS_RHOS    : rhos,
                    DETAILS_CS      : cs }

        # Save Dictionary
        aux.dictToNPZ(details, sav)


    return sav



def _loadBHDetails_ASCII(asciiFile, verbose=VERBOSE):

    ### Files have some blank lines in them... Clean ###
    lines = open(asciiFile).readlines()                                                             # Read all lines at once
    nums = len(lines)

    # Allocate storage
    ids    = np.zeros(nums, dtype=TYPE_ID)
    times  = np.zeros(nums, dtype=DBL)
    masses = np.zeros(nums, dtype=DBL)
    mdots  = np.zeros(nums, dtype=DBL)
    rhos   = np.zeros(nums, dtype=DBL)
    cs     = np.zeros(nums, dtype=DBL)

    count = 0
    # Iterate over lines, storing only those with content (should be all)
    for lin in lines:
        lin = lin.strip()
        if( len(lin) > 0 ):
            tid,tim,mas,dot,rho,tcs = _parseIllustrisBHDetailsLine(lin)
            ids[count] = tid
            times[count] = tim
            masses[count] = mas
            mdots[count] = dot
            rhos[count] = rho
            cs[count] = tcs
            count += 1

    # Trim excess (shouldn't be needed)
    if( count != nums ):
        trim = np.s_[count:]
        ids    = np.delete(ids, trim)
        times  = np.delete(times, trim)
        masses = np.delete(masses, trim)
        mdots  = np.delete(mdots, trim)
        rhos   = np.delete(rhos, trim)
        cs     = np.delete(cs, trim)


    return ids, times, masses, mdots, rhos, cs



def _parseIllustrisBHDetailsLine(instr):
    """
    Parse a line from an Illustris blachole_details_#.txt file

    The line is formatted (in C) as:
        "BH=%llu %g %g %g %g %g\n",
        (long long) P[n].ID, All.Time, BPP(n).BH_Mass, mdot, rho, soundspeed

    return ID, time, mass, mdot, rho, cs
    """
    args = instr.split()

    # First element is 'BH=########', trim to just the id number
    args[0] = args[0].split("BH=")[-1]

    return TYPE_ID(args[0]), DBL(args[1]), DBL(args[2]), DBL(args[3]), DBL(args[4]), DBL(args[5])






###  ==============================================================  ###
###  =============  BH / MERGER - DETAILS MATCHING  ===============  ###
###  ==============================================================  ###



def loadBHDetails(run, snap, verbose=VERBOSE):
    """
    Load Blackhole Details dictionary for the given snapshot.

    If the file does not already exist, it is recreated from the temporary ASCII files, or directly
    from the raw illustris ASCII files as needed.

    Arguments
    ---------
    run     : <int>, illustris simulation number {1,3}
    snap    : <int>, illustris snapshot number {0,135}
    verbose : <bool>, (optional=VERBOSE), print verbose output

    Returns
    -------
    dets    : <dict>, BHDetails dictionary object for target snapshot

    """


    if( verbose ): print " - - BHDetails.loadBHDetails()"

    detsName = GET_DETAILS_SAVE_FILENAME(run, snap, VERSION)
    if( verbose ): print " - - - Loading details from '%s'" % (detsName)

    recreate = False
    # Make sure file exists
    if( os.path.exists(detsName) ):
        dets = aux.npzToDict(detsName)
        loadVers = dets[DETAILS_VERSION]
        # Make sure versions match
        if( loadVers != VERSION ):
            print "BHDetails.loadBHDetails() : loaded  version %s" % (str(loadVers))
            print "BHDetails.loadBHDetails() : current version %s" % (str(VERSION))
            recreate = True
        else:
            if( verbose ): print " - - - File loaded."

    else:
        recreate = True
        print "BHDetails.loadBHDetails() : file does not exist"


    # If file does not exist, or is wrong version, recreate it
    if( recreate ):
        if( verbose): 
            print " - - - Creating details for ill-%d, snap-%d, v%s" % (run, snap, str(VERSION))

        # Convert ASCII to NPZ
        saveFile = _convertDetailsASCIItoNPZ_snapshot(run, snap, loadsave=True, verbose=verbose)
        # Load details from newly created save file
        dets = aux.npzToDict(saveFile)


    return dets

# loadBHDetails()



def _getPrecision(args):
    """

    """

    diffs = np.fabs(np.diff(sorted(args)))
    inds  = np.nonzero(diffs)
    if( len(inds) > 0 ): minDiff = np.min( diffs[inds] )
    else:                minDiff = np.power(10.0, _DEF_PRECISION)
    order = int(np.log10(0.49*minDiff))
    return order

# _getPrecision()


