//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
// $Id: B1SteppingAction.cc 74483 2013-10-09 13:37:06Z gcosmo $
//
/// \file B1SteppingAction.cc
/// \brief Implementation of the B1SteppingAction class

#include "B1TrackingAction.hh"
#include "B1EventAction.hh"
#include "B1DetectorConstruction.hh"
#include "B1Analysis.hh"

#include "G4RunManager.hh"
#include "G4LogicalVolume.hh"
#include "G4SystemOfUnits.hh"
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

B1TrackingAction::B1TrackingAction(B1EventAction* eventAction)
: G4UserTrackingAction(),
  fEventAction(eventAction),
  fScoringVolume1(0),
  fScoringVolume2(0)
{}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

B1TrackingAction::~B1TrackingAction()
{}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void B1TrackingAction::PreUserTrackingAction(const G4Track* tr)
{
  if (tr->GetParentID() == 0) return;

  if (!fScoringVolume1) {
    const B1DetectorConstruction* detectorConstruction
      = static_cast<const B1DetectorConstruction*>
        (G4RunManager::GetRunManager()->GetUserDetectorConstruction());
    fScoringVolume1 = detectorConstruction->GetScoringVolume1();
    fScoringVolume2 = detectorConstruction->GetScoringVolume2();
  }

  G4LogicalVolume* volume
    = tr->GetTouchableHandle()
      ->GetVolume()->GetLogicalVolume();
  if (volume == fScoringVolume1) {
    auto E = tr->GetTotalEnergy()/GeV;
    if (E > 10.) {
      auto analysisManager = G4RootAnalysisManager::Instance();
      auto PDGID = tr->GetParticleDefinition()->GetPDGEncoding();
      if (PDGID == -11) analysisManager->FillH3(0, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 11) analysisManager->FillH3(1, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == -13) analysisManager->FillH3(2, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 13) analysisManager->FillH3(3, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 22) analysisManager->FillH3(4, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 111) analysisManager->FillH3(5, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == -211) analysisManager->FillH3(6, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 211) analysisManager->FillH3(7, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 221) analysisManager->FillH3(8, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == -321) analysisManager->FillH3(9, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 321) analysisManager->FillH3(10, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == -2112) analysisManager->FillH3(11, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 2112) analysisManager->FillH3(12, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == -2212) analysisManager->FillH3(13, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 2212) analysisManager->FillH3(14, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 113) analysisManager->FillH3(30, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 223) analysisManager->FillH3(31, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 333) analysisManager->FillH3(32, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
      if (PDGID == 443) analysisManager->FillH3(33, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm);
    }	  
  }

  if (volume == fScoringVolume2) {
    auto E = tr->GetTotalEnergy()/GeV;
    if (E > 10.) {
      auto analysisManager = G4RootAnalysisManager::Instance();
      auto PDGID = tr->GetParticleDefinition()->GetPDGEncoding();
      if (PDGID == -11) analysisManager->FillH3(15, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 11) analysisManager->FillH3(16, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == -13) analysisManager->FillH3(17, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 13) analysisManager->FillH3(18, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 22) analysisManager->FillH3(19, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 111) analysisManager->FillH3(20, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == -211) analysisManager->FillH3(21, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 211) analysisManager->FillH3(22, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 221) analysisManager->FillH3(23, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == -321) analysisManager->FillH3(24, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 321) analysisManager->FillH3(25, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == -2112) analysisManager->FillH3(26, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 2112) analysisManager->FillH3(27, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == -2212) analysisManager->FillH3(28, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 2212) analysisManager->FillH3(29, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm -33.);
      if (PDGID == 113) analysisManager->FillH3(34, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm - 33.);
      if (PDGID == 223) analysisManager->FillH3(35, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm - 33.);
      if (PDGID == 333) analysisManager->FillH3(36, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm - 33.);
      if (PDGID == 443) analysisManager->FillH3(37, E, tr->GetMomentumDirection().theta(), tr->GetPosition()[2]/cm - 33.);
    }	  
  }



}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

