#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
"""
@brief

@namespace ...
@authors Reda Drissi <mohamed-reda.drissi@atos.net>
@copyright 2019  Bull S.A.S.  -  All rights reserved.
           This is not Free or Open Source software.
           Please contact Bull SAS for details about its license.
           Bull - Rue Jean Jaurès - B.P. 68 - 78340 Les Clayes-sous-Bois


Description Converts qiskit circuit into a qlm circuit object,
            you can use : qlm_circuit = to_qlm_circ(your_qiskit_circuit)
            This is a placeholder, names and packaging might change to
            keep consistency

Overview
=========


"""

import qiskit
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, Aer
from qat.lang.AQASM import *
from qat.lang.AQASM.gates import *
from qat.comm.shared.ttypes import Job, Batch, Result
from qat.comm.datamodel.ttypes import Circuit
import numpy as np


def get_qindex(circ, name, index):
    """ Find the qubit index"""
    ret = 0
    for reg in circ.qregs:
        if name != reg.name:
            ret += reg.size
        else:
            return ret + index


def get_cindex(circ, name, index):
    """ Find the classical bit index"""
    ret = 0
    for reg in circ.cregs:
        if name != reg.name:
            ret += reg.size
        else:
            return ret + index


# Let's add the U gate, u1/2/3 would be dealt with through setting
# the appropriate params to 0
def gen_U(theta, phi, lamda):
    """ generate the U gate matrix """
    m11 = (np.e ** (1j * (phi + lamda) / 2)) * np.cos(theta / 2)
    m12 = (-1) * (np.e ** (1j * (phi - lamda) / 2)) * np.sin(theta / 2)
    m21 = (np.e ** (1j * (phi - lamda) / 2)) * np.sin(theta / 2)
    m22 = (np.e ** (1j * (phi + lamda) / 2)) * np.cos(theta / 2)
    return np.array([[m11, m12], [m21, m22]], dtype=np.complex128)


def gen_RZZ(theta):
    """ generates the RZZ gate matrix """
    return np.diag([1, np.exp(1j * theta), np.exp(1j * theta), 1])


U = AbstractGate("U", [float] * 3, arity=1, matrix_generator=gen_U)
RZZ = AbstractGate("RZZ", [float], arity=2, matrix_generator=gen_RZZ)
# get qbits


def process_U(params):
    """ return corresponding U matrix"""
    return U(params[0], params[1], params[2])


def process_U2(params):
    """ Returns the corresponding u2 matrix """
    return U(0, params[0], params[1])


gate_dic = {
    "h": H,
    "x": X,
    "y": Y,
    "z": Z,
    "xbase": X,
    "swap": SWAP,
    "id": I,
    "s": S,
    "sdg": S.dag(),
    "t": T,
    "tdg": T.dag(),
    "rx": RX,
    "ry": RY,
    "rz": RZ,
    "rzz": RZZ,
    "u0": I,
    "u1": RY,
    "u2": process_U2,
    "u3": process_U,
    "U": process_U,
}


def get_gate(gate, params):
    """ generates pyAQASM corresponding gate """
    if gate == "u0":
        return I
    elif gate[0] == "c":
        return get_gate(gate[1:], params).ctrl()
    elif len(params) == 0:
        return gate_dic[gate]
    elif len(params) == 1:
        return gate_dic[gate](params[0])
    else:
        return gate_dic[gate](params)


def old_to_qlm_circ(qiskit_circuit, sep_measure=False):
    """ translates a qiskit circuit into a qlm circuit"""
    prog = Program()
    qbits_num = 0
    to_measure = []
    for reg in qiskit_circuit.qregs:
        qbits_num = qbits_num + reg.size
    qbits = prog.qalloc(qbits_num)

    cbits_num = 0
    for reg in qiskit_circuit.cregs:
        cbits_num = cbits_num + reg.size
    cbits = prog.calloc(cbits_num)
    for op in qiskit_circuit.data:
        qb = []  # qbits arguments
        cb = []  # cbits arguments
        prms = []  # gate parameters
        # Get qbit arguments
        for reg in op.qargs:
            qb.append(qbits[get_qindex(qiskit_circuit, reg[0].name, reg[1])])

        # Get cbit arguments
        for reg in op.cargs:
            cb.append(qbits[get_cindex(qiskit_circuit, reg[0].name, reg[1])])

        # Get parameters
        for p in op.param:
            prms.append(float(p))
        # Apply measure #
        if op.name == "measure":
            if sep_measure:
                to_measure.append(qb)
            else:
                prog.measure(qb, cb)
        else:
            # Apply gates #
            prog.apply(get_gate(op.name, prms), qb)
    if sep_measure:
        return prog.to_circ(), to_measure
    else:
        return prog.to_circ()


def new_to_qlm_circ(qiskit_circuit, sep_measure=False):
    """ translates a qiskit circuit into a qlm circuit"""
    prog = Program()
    qbits_num = 0
    to_measure = []
    for reg in qiskit_circuit.qregs:
        qbits_num = qbits_num + reg.size
    qbits = prog.qalloc(qbits_num)

    cbits_num = 0
    for reg in qiskit_circuit.cregs:
        cbits_num = cbits_num + reg.size
    cbits = prog.calloc(cbits_num)
    for op in qiskit_circuit.data:
        qb = []  # qbits arguments
        cb = []  # cbits arguments
        prms = []  # gate parameters
        # Get qbit arguments
        for reg in op[1]:
            qb.append(qbits[get_qindex(qiskit_circuit, reg[0].name, reg[1])])

        # Get cbit arguments
        for reg in op[2]:
            cb.append(qbits[get_cindex(qiskit_circuit, reg[0].name, reg[1])])

        # Get parameters
        for p in op[0]._params:
            prms.append(float(p))
        # Apply measure #
        if op[0].name == "measure":
            if sep_measure:
                to_measure.append(qb)
            else:
                prog.measure(qb, cb)
        else:
            # Apply gates #
            prog.apply(get_gate(op[0].name, prms), qb)
    if sep_measure:
        return prog.to_circ(), to_measure
    else:
        return prog.to_circ()


def to_qlm_circ(qiskit_circuit, sep_measure=False):
    from pkg_resources import parse_version

    if parse_version(qiskit.__version__) < parse_version("0.7.9"):
        return old_to_qlm_circ(qiskit_circuit, sep_measure)
    else:
        return new_to_qlm_circ(qiskit_circuit, sep_measure)


def qlm_circ_sep_meas(qiskit_circuit):
    return to_qlm_circ(qiskit_circuit, True)


def gen_qiskit_gateset(qc):
    return {
        'H': qc.h,
        'X': qc.x,
        'Y': qc.y,
        'Z': qc.z,
        'SWAP': qc.swap,
        'S': qc.s,
        'D-S': qc.sdg,
        'T': qc.t,
        'D-T': qc.tdg,
        'RX': qc.rx,
        'RY': qc.ry,
        'RZ': qc.rz,
    }

from qat.core.util import extract_syntax
def to_qiskit_circuit(qlm_circuit):
    qreg = QuantumRegister(qlm_circuit.nbqbits)
    creg = ClassicalRegister(qlm_circuit.nbcbits)
    qc = QuantumCircuit(qreg, creg)
    dic = gen_qiskit_gateset(qc)
    for op in qlm_circuit.ops:
        name, params = extract_syntax(qlm_circuit.gateDic[op.gate], qlm_circuit.gateDic)
        if op.type == 0:
            try:
                dic[name](params + [qreg[i] for i in op.qbits])
            except KeyError:
                raise ValueError(
                    "Gate {} not supported by qiskit API".format(name)
                )
        elif op.type == 1:
            for index in range(len(op.qbits)):
                qc.measure(op.qbits[index], op.cbits[index])
    return qc


def job_to_qiskit_circuit(qlm_job):
    # TODO account for type sample/observable
    # TODO account for nbshots
    # TODO account for
    return to_qiskit_circuit(qlm_job.circuit)