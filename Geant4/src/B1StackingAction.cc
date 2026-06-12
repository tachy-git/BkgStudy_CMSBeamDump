#include "G4UserStackingAction.hh"
#include "G4Track.hh"
#include "globals.hh"
#include "G4SystemOfUnits.hh"

class StackingAction : public G4UserStackingAction
{
public:
    virtual G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track* track)
    {
        // keep primary beam always
        if (track->GetParentID() == 0)
            return fUrgent;

        // kill low-energy secondaries
        if (track->GetKineticEnergy() < 9*GeV)
            return fKill;

        return fUrgent;
    }
};
