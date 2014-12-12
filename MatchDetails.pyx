# =================================================================================================
# MatchDetails.pyx
# ----------------
#
#
#
# ------------------
# Luke Zoltan Kelley
# LKelley@cfa.harvard.edu
# =================================================================================================




import numpy as np
cimport numpy as np






def getDetailIndicesForMergers(np.ndarray[long, ndim=1] active, np.ndarray[long, ndim=1] inid, 
                               np.ndarray[long, ndim=1] outid, np.ndarray[long, ndim=1] detid ):
    """
    Match merger BHs to details entries for a particular snapshot.

    This function takes as input the indices of active BH mergers as
    ``active``.  The in and out BH indices for *all* mergers are given in
    ``inid`` and ``outid``.  The ``outid``s are cross checked with each of
    IDs for the details entries given in ``detid``.  When matches are missing,
    it is assumed that the 'out' BH later merged into another system, in which
    case the resulting BH ID could have been different.  The initial 'out' BH
    which was targeted are returned in the resulting array ``targetID``,
    whereas the actual BH ID which was found (perhaps after numerous mergers
    inbetween) is returned in the array `foundID`.  Finally, the index of the
    Details entry where those IDs are finally found are returned in the array
    ``retinds`` which can then be used to extract the details information for
    each binary.

    The Details files have (up to) numerous entries for each BH.  Currently
    only one of them is selected and added to the ``retinds`` array.  The first
    match is returned --- which *may* be the earliest in time.


    Parameters
    ----------
    active : array, long
        Array of indices corresponding to 'active' (already formed) binary
        systems to be matched.  Length is the number of active mergers ``N``.
    inid : array, long
        Array of indices for Merger 'in' BHs.  Length is the total number
        of Mergers, same as ``outid``.
    outid : array, long
        Array of indices for Merger 'out' BHs.  Length is the total number
        of Mergers, same as ``inid``.
    detit : array, long
        Array of indices for each Details entry.  Length is the number of
        details entries.

    Returns
    -------
    3 arrays are returned, each of length equal to the total number of Mergers.
    Entries for *inactive* systems have values set to `-1`.  The values for
    active BHs are described below.

    targetID : array, long
        Indices of each merger 'out' BH which is the target.  Length is the
        total number of Mergers.
    foundID : array, long
        Indices of each merger which were actually matched in the Details
        entries.  ``targetID`` gives each mergers' 'out' BH, but many of those
        later merged again --- leading to a different ID number for the
        resulting system.  Those resulting IDs are given by ``foundID``.
    retinds : array, long
        Indices of the Details entries which correspond to each Merger.

    """
    
    
    # Get the lengths of all input arrays
    cdef int numMergers = inid.shape[0]                                                             # Length of both 'inid' and 'outid'
    cdef int numDetails = detid.shape[0]
    cdef int numActive  = active.shape[0]

    # Find indices to sort ID arrays for faster searching
    cdef np.ndarray sort_inid = np.argsort(inid)
    cdef np.ndarray sort_outid = np.argsort(outid)
    cdef np.ndarray sort_detid = np.argsort(detid)

    cdef long ind, target, found
    cdef int MAX_COUNT = 100

    # Initialize arrays to store results; default to '-1'
    cdef np.ndarray retinds = -1*np.ones(numActive, dtype=long)
    cdef np.ndarray targetID = -1*np.ones(numActive, dtype=long)
    cdef np.ndarray foundID = -1*np.ones(numActive, dtype=long)

    ### Iterate over Each Active Merger Binary System ###
    for mm in range(numActive):

        target = outid[active[mm]]
        found = target
        # Store the target ID in the output array
        targetID[mm] = target

        # Try to find binary (out bh) in details
        ind = np.searchsorted( detid, target, 'left', sorter=sort_detid )

        # If search failed, set ind to invalid
        if( detid[sort_detid[ind]] != found ): ind = -1

        # If search failed; see if this 'out' bh merged again, update 'out' id to that
        count = 0
        while( ind < 0 ):
            
            # Check if we are stuck, if so, break
            if( count >= MAX_COUNT ):
                ind = -1
                break

            ### See if this 'out' BH merged again ###
            #   i.e. if it was the 'in' BH of a later merger

            ind = np.searchsorted( inid, found, 'left', sorter=sort_inid )

            # If target is not an 'in bh' then it is missing, break
            if( inid[sort_inid[ind]] != found ):
                ind = -1
                break


            ### Redo details search with new 'out id'

            # Set new 'out id' to match partner of 'in id'
            found = outid[sort_inid[ind]]
            
            # Redo search
            ind = np.searchsorted( detid, found, 'left', sorter=sort_detid )

            # Check if search succeeded
            if( detid[sort_detid[ind]] != found ): ind = -1

            # Increment counter to make sure not stuck
            count += 1

        # } while

        # If we have a match, store results
        if( ind >= 0 ): 
            # Store matching Details index
            retinds[mm] = sort_detid[ind]
            # Store the ID which was eventually matched
            foundID[mm] = found

    # } mm

    return targetID, foundID, retinds






