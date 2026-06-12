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
// $Id: B1RunAction.cc 87359 2014-12-01 16:04:27Z gcosmo $
//
/// \file B1RunAction.cc
/// \brief Implementation of the B1RunAction class

#include "B1RunAction.hh"
#include "B1Run.hh"
#include "B1Analysis.hh"

#include "G4RunManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"

#include <math.h>
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

B1RunAction::B1RunAction()
: G4UserRunAction()
{ 
  // add new units for dose
  // 
  const G4double milligray = 1.e-3*gray;
  const G4double microgray = 1.e-6*gray;
  const G4double nanogray  = 1.e-9*gray;  
  const G4double picogray  = 1.e-12*gray;
   
  new G4UnitDefinition("milligray", "milliGy" , "Dose", milligray);
  new G4UnitDefinition("microgray", "microGy" , "Dose", microgray);
  new G4UnitDefinition("nanogray" , "nanoGy"  , "Dose", nanogray);
  new G4UnitDefinition("picogray" , "picoGy"  , "Dose", picogray);        

  auto analysisManager = G4RootAnalysisManager::Instance(); 
  G4cout << "Using " << analysisManager->GetType() << G4endl;
  analysisManager->SetVerboseLevel(1);

  std::vector<G4double> xAxis; 
  for (G4double i = 0.1; i < 7E3; i *= pow(10,0.1) ){xAxis.push_back(i);}
  std::vector<G4double> yAxis;
  for (G4double i = 1E-6; i < 1.0; i *= pow(10,0.1)) {yAxis.push_back(i);}
  std::vector<G4double> zAxis;
  for (G4double i = 0.0; i < 121; i += 1) {zAxis.push_back(i);}
  analysisManager->CreateH3("ECal_ep_-11","e^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_e_11","e^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_mup_-13","#mu^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_mum_13","#mu^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_photon_22","#gamma E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_pi0_111","#pi^{0} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_pim_-211","#pi^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_pip_211","#pi^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_eta_221","#eta E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_km_-321","K^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_kp_321","K^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_nb_-2112","#bar{n} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_n_2112","n E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_pb_-2212","#bar{p} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_p_2212","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);

  analysisManager->CreateH3("HCal_ep_-11","e^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_e_11","e^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_mup_-13","#mu^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_mum_13","#mu^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_photon_22","#gamma E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_pi0_111","#pi^{0} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_pim_-211","#pi^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_pip_211","#pi^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_eta_221","#eta E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_km_-321","K^{-} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_kp_321","K^{+} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_nb_-2112","#bar{n} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_n_2112","n E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_pb_-2212","#bar{p} E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_p_2212","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);


  analysisManager->CreateH3("ECal_rho_113","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_omega_223","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_phi_333","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("ECal_Jpsi_443","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);

  analysisManager->CreateH3("HCal_rho_113","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_omega_223","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_phi_333","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);
  analysisManager->CreateH3("HCal_Jpsi_443","p E (GeV)  Theta (rad) z (cm)", xAxis, yAxis, zAxis);


}
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

B1RunAction::~B1RunAction()
{}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4Run* B1RunAction::GenerateRun()
{
  return new B1Run; 
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void B1RunAction::BeginOfRunAction(const G4Run*)
{ 
  //inform the runManager to save random number seed
  G4RunManager::GetRunManager()->SetRandomNumberStore(false);
  auto analysisManager = G4RootAnalysisManager::Instance();
  analysisManager->OpenFile();
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void B1RunAction::EndOfRunAction(const G4Run* run)
{
  G4int nofEvents = run->GetNumberOfEvent();
  if (nofEvents == 0) return;
  auto analysisManager = G4RootAnalysisManager::Instance();
  analysisManager->Write();
  analysisManager->CloseFile(); 
 
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
