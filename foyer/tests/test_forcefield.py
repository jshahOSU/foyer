import glob
import os
from pkg_resources import resource_filename

import mbuild as mb
from mbuild.examples import Alkane
import parmed as pmd
import pytest

from foyer import Forcefield
from foyer.forcefield import generate_topology
from foyer.forcefield import _check_independent_residues
from foyer.tests.utils import get_fn


FF_DIR = resource_filename('foyer', 'forcefields')
FORCEFIELDS = glob.glob(os.path.join(FF_DIR, '*.xml'))


def test_load_files():
    for ff_file in FORCEFIELDS:
        ff1 = Forcefield(forcefield_files=ff_file)
        assert len(ff1._atomTypes) > 0

        ff2 = Forcefield(forcefield_files=ff_file)
        assert len(ff1._atomTypes) == len(ff2._atomTypes)


def test_duplicate_type_definitions():
    with pytest.raises(ValueError):
        ff4 = Forcefield(name='oplsaa', forcefield_files=FORCEFIELDS)



def test_from_parmed():
    mol2 = pmd.load_file(get_fn('ethane.mol2'), structure=True)
    oplsaa = Forcefield(name='oplsaa')
    ethane = oplsaa.apply(mol2)

    assert sum((1 for at in ethane.atoms if at.type == 'opls_135')) == 2
    assert sum((1 for at in ethane.atoms if at.type == 'opls_140')) == 6
    assert len(ethane.bonds) == 7
    assert all(x.type for x in ethane.bonds)
    assert len(ethane.angles) == 12
    assert all(x.type for x in ethane.angles)
    assert len(ethane.rb_torsions) == 9
    assert all(x.type for x in ethane.dihedrals)

    mol2 = pmd.load_file(get_fn('ethane.mol2'), structure=True)
    mol2.box_vectors = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
    oplsaa = Forcefield(name='oplsaa')
    ethane = oplsaa.apply(mol2)

    assert ethane.box_vectors == mol2.box_vectors


def test_from_mbuild():
    mol2 = mb.load(get_fn('ethane.mol2'))
    oplsaa = Forcefield(name='oplsaa')
    ethane = oplsaa.apply(mol2)

    assert sum((1 for at in ethane.atoms if at.type == 'opls_135')) == 2
    assert sum((1 for at in ethane.atoms if at.type == 'opls_140')) == 6
    assert len(ethane.bonds) == 7
    assert all(x.type for x in ethane.bonds)
    assert len(ethane.angles) == 12
    assert all(x.type for x in ethane.angles)
    assert len(ethane.rb_torsions) == 9
    assert all(x.type for x in ethane.dihedrals)

def test_write_refs():
    mol2 = mb.load(get_fn('ethane.mol2'))
    oplsaa = Forcefield(name='oplsaa')
    ethane = oplsaa.apply(mol2, references_file='ethane.bib')
    assert os.path.isfile('ethane.bib')

def test_preserve_resname():
    untyped_ethane = pmd.load_file(get_fn('ethane.mol2'), structure=True)
    untyped_resname = untyped_ethane.residues[0].name
    oplsaa = Forcefield(name='oplsaa')
    typed_ethane = oplsaa.apply(untyped_ethane)
    typed_resname = typed_ethane.residues[0].name
    assert typed_resname == untyped_resname

def test_apply_residues():
    from mbuild.examples import Ethane
    ethane = Ethane()
    opls = Forcefield(name='oplsaa')
    typed = opls.apply(ethane, residues='CH3')
    assert len([res for res in typed.residues if res.name == 'CH3']) == 2

def test_from_mbuild_customtype():
    mol2 = mb.load(get_fn('ethane_customtype.pdb'))
    customtype_ff = Forcefield(forcefield_files=get_fn('validate_customtypes.xml'))
    ethane = customtype_ff.apply(mol2)

    assert sum((1 for at in ethane.atoms if at.type == 'C3')) == 2
    assert sum((1 for at in ethane.atoms if at.type == 'Hb')) == 6
    assert len(ethane.bonds) == 7
    assert all(x.type for x in ethane.bonds)
    assert len(ethane.angles) == 12
    assert all(x.type for x in ethane.angles)
    assert len(ethane.rb_torsions) == 9
    assert all(x.type for x in ethane.dihedrals)

def test_improper_dihedral():
    untyped_benzene = pmd.load_file(get_fn('benzene.mol2'), structure=True)
    ff_improper = Forcefield(forcefield_files=get_fn('improper_dihedral.xml'))
    benzene = ff_improper.apply(untyped_benzene)
    assert len(benzene.dihedrals) == 18
    assert len([dih for dih in benzene.dihedrals if dih.improper]) == 6
    assert len([dih for dih in benzene.dihedrals if not dih.improper]) == 12

def test_residue_map():
    ethane = pmd.load_file(get_fn('ethane.mol2'), structure=True)
    ethane *= 2
    oplsaa = Forcefield(name='oplsaa')
    topo, NULL = generate_topology(ethane)
    with_map = pmd.openmm.load_topology(topo,
            oplsaa.createSystem(topo, use_residue_map=True))
    without_map = pmd.openmm.load_topology(topo,
            oplsaa.createSystem(topo, use_residue_map=False))
    for atom_with, atom_without in zip(with_map.atoms, without_map.atoms):
        assert atom_with.type == atom_without.type
        b_with = atom_with.bond_partners
        b_without = atom_without.bond_partners
        assert [a0.type for a0 in b_with] == [a1.type for a1 in b_without]
        assert [a0.idx for a0 in b_with] == [a1.idx for a1 in b_without]

def test_independent_residues():
    """Test to see that _check_independent_residues works."""
    butane = Alkane(4)
    structure = butane.to_parmed()
    topo, NULL = generate_topology(structure)
    assert _check_independent_residues(topo)
    structure = butane.to_parmed(residues=['RES', 'CH3'])
    topo, NULL = generate_topology(structure)
    assert not _check_independent_residues(topo)
