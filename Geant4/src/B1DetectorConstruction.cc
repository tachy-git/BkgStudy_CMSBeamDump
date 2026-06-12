#include "B1DetectorConstruction.hh"

#include "G4NistManager.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"
#include "G4GenericMessenger.hh"


B1DetectorConstruction::B1DetectorConstruction()
: G4VUserDetectorConstruction(),
  fScoringVolume1(0),
  fScoringVolume2(0),
  env_sizeZm(23.0),
  env_matm("G4_AIR")
{
  messenger = new G4GenericMessenger(this, "/detector/", "Detector properties");
      messenger->DeclareProperty("envSizeZ",env_sizeZm)
        .SetGuidance("Set environment size Z")
        .SetStates(G4State_PreInit, G4State_Idle);

    messenger->DeclareProperty("envMaterial", env_matm)
        .SetGuidance("Set environment material")
        .SetStates(G4State_PreInit, G4State_Idle);

}
B1DetectorConstruction::~B1DetectorConstruction()
{ 
  delete messenger;
}


G4VPhysicalVolume* B1DetectorConstruction::Construct()
{  
  G4double env_sizeZ = env_sizeZm*cm;
  G4NistManager* nist = G4NistManager::Instance();
  G4bool checkOverlaps = true;
  G4double world_sizeXY = 5.0*m;
  G4double world_sizeZ  = 6.0*m;
  G4Material* world_mat = nist->FindOrBuildMaterial("G4_AIR");
  G4Material* ecal_mat = nist->FindOrBuildMaterial("G4_PbWO4");
  G4Material* hcal_mat = nist->FindOrBuildMaterial("G4_Cu");
  G4cout << "[Construct] Using env_sizeZ: " << env_sizeZ / cm << " cm" << G4endl;
  G4cout << "[Construct] Using env_matm: " << env_matm << G4endl;


  G4Box* solidWorld =    
    new G4Box("World",                       //its name
       0.5*world_sizeXY, 0.5*world_sizeXY, 0.5*world_sizeZ);     //its size
      
  G4LogicalVolume* logicWorld =                         
    new G4LogicalVolume(solidWorld,          //its solid
                        world_mat,           //its material
                        "World");            //its name
                                   
  G4VPhysicalVolume* physWorld = 
    new G4PVPlacement(0,                     //no rotation
                      G4ThreeVector(),       //at (0,0,0)
                      logicWorld,            //its logical volume
                      "World",               //its name
                      0,                     //its mother  volume
                      false,                 //no boolean operation
                      0,                     //copy number
                      checkOverlaps);        //overlaps checking
                     

  G4Box* solidECal =
    new G4Box("ECal", 0.5*4.*m, 0.5*4.*m, 0.5*env_sizeZ);

  G4LogicalVolume* logicECal =
    new G4LogicalVolume(solidECal, ecal_mat, "ECal");

  new G4PVPlacement(0,
                    G4ThreeVector(0, 0, 0.5*env_sizeZ),
                    logicECal, "ECal", logicWorld, false, 0, checkOverlaps);

  G4Box* solidHCal =
    new G4Box("HCal", 0.5*4.*m, 0.5*4.*m, 0.5*2.3*m);

  G4LogicalVolume* logicHCal =
    new G4LogicalVolume(solidHCal, hcal_mat, "HCal");

  new G4PVPlacement(0,
                    G4ThreeVector(0, 0, env_sizeZ + 10*cm + 0.5*2.3*m),
                    logicHCal, "HCal", logicWorld, false, 0, checkOverlaps);


  fScoringVolume1 = logicECal;
  fScoringVolume2 = logicHCal;
  return physWorld;
}

 


