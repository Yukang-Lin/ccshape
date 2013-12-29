#!/usr/local/epd/bin/python


__author__ = "Brandon Ayers"
__copyright__ = "Copyright 2013, Shantanu H. Joshi, Brandon Ayers, \
                 Ahmanson-Lovelace Brain Mapping Center, University of California Los Angeles"
__email__ = "ayersb@ucla.edu"

from math import pi
import os
import sys
import cPickle
import matplotlib.pyplot as plt
import numpy as np
from curvematch.match import match_curve_pair
from curvematch.curve import Curve
from curvematch.curve import Curve
from curvematch.qshape import QShape
from curvematch import geodesics
from shapeio.curveio import WriteUCF



class CCThickness():
    def __init__(self, subject_name, curvefile_path_top, curvefile_path_bottom, resample_siz=500, geodesic_steps=10):
        self.settings = geodesics.Geodesic()
        self.settings.steps = geodesic_steps
        self.settings.closed = False

        self.subject_name = subject_name
        self.return_shapes = True
        self.resample_siz = resample_siz
        self.rotation = False

        self.curvefile_path_top = os.path.abspath(curvefile_path_top)
        self.curvefile_path_bottom = os.path.abspath(curvefile_path_bottom)

        self.gamma = []
        self.curve_top = []
        self.curve_bot = []
        self.plane_dim_data = []

        self.curve_bot_gamma_adjusted = []
        self.naive_thickness = []
        self.thickness = []
        self.main_method()

    def main_method(self):
        self.get_matched_curve_pair_data()
        self.curve_bot_gamma_adjusted = self.get_curve_of_gamma(self.curve_bot)
        self.compute_thickness()

    def get_matched_curve_pair_data(self):
        curve_pair_data = match_curve_pair(self.curvefile_path_top, self.curvefile_path_bottom,
                                           self.settings, self.rotation,
                                           self.resample_siz, self.return_shapes)
        self.gamma = curve_pair_data[0].gamma
        self.curve_top = curve_pair_data[1]
        self.curve_bot = curve_pair_data[2]
        diff_between_dims = np.abs(np.sum(self.curve_top.coords - self.curve_bot.coords, 1))
        if np.min(diff_between_dims) > 1:
            raise ValueError("These segmentations don't seem to be from the same plane.")
        least_var_dim = np.argmin(diff_between_dims)
        coords_top, coords_bot = [], []
        for i in xrange(self.curve_top.dim):
            if i == least_var_dim:
                self.plane_dim_data = [i, self.curve_top.coords[i], self.curve_bot.coords[i]]
            else:
                coords_top.append(self.curve_top.coords[i])
                coords_bot.append(self.curve_bot.coords[i])
        self.curve_top.dim -= 1
        self.curve_bot.dim -= 1
        self.curve_top.coords = np.array(coords_top)
        self.curve_bot.coords = np.array(coords_bot)


    def get_curve_of_gamma(self, curve1):
        ##Please check that this is correct!
        newcoords = np.zeros((curve1.dim, curve1.siz))
        for i in range(0, curve1.dim):
            newcoords[i, :] = np.interp(self.gamma, np.linspace(0, 2*pi, curve1.siz), curve1.coords[i, :])
        newcurve = Curve()
        newcurve.coords = newcoords
        newcurve.dim = curve1.dim
        newcurve.siz = curve1.siz
        return newcurve

    def compute_thickness(self, include_naive=True):
        #Just finds the euclidean distance between points
        if include_naive:
            self.naive_thickness = np.sqrt(np.sum((self.curve_top.coords - self.curve_bot.coords)**2, axis=0))
        self.thickness = np.sqrt(np.sum((self.curve_top.coords - self.curve_bot_gamma_adjusted.coords)**2, axis=0))
        print "Naive: ", np.average(self.naive_thickness),'\n'
        print "Gamma: ", np.average(self.thickness),'\n'
        print "% Difference: ", 100 * (np.average(self.naive_thickness-self.thickness))/(.5*(np.average(np.average(self.naive_thickness)+np.average(self.thickness)))),'\n\n'

    def save_thickness(self):
        np.savetxt(self.subject_name+"_thickness_values.txt", self.thickness)

    def plot_thicknesses(self, include_naive_plot=True):
        set_fontsize = 10
        if include_naive_plot:
            test_code_only = "\n% Difference: " + str(100 * (np.average(self.naive_thickness-self.thickness))/(.5*(np.average(np.average(self.naive_thickness)+np.average(self.thickness)))))
            plt.subplot(211)
            plt.title(self.subject_name+test_code_only, fontsize=set_fontsize+1)
            plt.subplots_adjust(hspace=0.4)
            plt.tick_params(labelsize=set_fontsize)
            plt.xlabel("Point to Point Matching" + '\n Avg Thickness = ' + str(np.average(self.naive_thickness)),fontsize=set_fontsize)
            self.add_thickness_plot_given_curves(self.curve_top, self.curve_bot)
            plt.subplot(212)
            plt.xlabel("Elastic Matching " + '\n Avg Thickness = ' + str(np.average(self.thickness)), fontsize=set_fontsize)
            self.add_thickness_plot_given_curves(self.curve_top, self.curve_bot_gamma_adjusted)
            plt.savefig(self.subject_name + ".pdf")
        else:
            plt.title(self.subject_name)
            self.add_thickness_plot_given_curves(self.curve_top, self.curve_bot_gamma_adjusted)
            plt.savefig(self.subject_name + ".pdf")

    def add_thickness_plot_given_curves(self, curve1, curve2):
            plt.plot(curve1.coords[0], curve1.coords[1])
            plt.plot(curve2.coords[0], curve2.coords[1])
            for i in xrange(0,len(curve1.coords[0])):
                plt.plot([curve1.coords[0][i], curve2.coords[0][i]],
                         [curve1.coords[1][i], curve2.coords[1][i]])

    def output_thickness_ucf(self, output_adjusted_coords = True):
        output_coords = []
        output_plane_data = np.array(list(self.plane_dim_data[1]) + list(self.plane_dim_data[2]))
        output_plane_dim = self.plane_dim_data[0]
        for coord_index in xrange(len(self.curve_top.coords)):
            if output_adjusted_coords:
                fname = self.subject_name + "_adjusted_thickness.ucf"
                output_coords.append(np.array(list(self.curve_top.coords[coord_index]) +
                                              list(self.curve_bot_gamma_adjusted.coords[coord_index][::-1])))
            else:
                fname = self.subject_name + "_native_thickness.ucf"
                output_coords.append(np.array(list(self.curve_top.coords[coord_index]) +
                                              list(self.curve_bot.coords[coord_index][::-1])))
        output_coords.insert(output_plane_dim, output_plane_data)
        output_coords = np.array(output_coords).transpose()
        output_thickness = np.array(list(self.thickness) + list(self.thickness)[::-1])
        WriteUCF(output_coords, "thickness", output_thickness, fname)


def main():
    if len(sys.argv) <= 1:
        return help()
    else:
        subject_name = sys.argv[1]
        subject_top_curve_ucf = sys.argv[2]
        subject_bot_curve_ucf = sys.argv[3]
        subject_curve_out_dir = sys.argv[4]
        subject_thickness = CCThickness(subject_name, subject_top_curve_ucf,
                                        subject_bot_curve_ucf)
        os.chdir(subject_curve_out_dir)
        subject_thickness.plot_thicknesses()
        subject_thickness.save_thickness()
        subject_thickness.output_thickness_ucf(True)
        subject_thickness.output_thickness_ucf(False)
        output_file = open(subject_thickness.subject_name + "_CCThickness_object.pickle", 'w')
        cPickle.dump(subject_thickness, output_file)
        output_file.close()

main()