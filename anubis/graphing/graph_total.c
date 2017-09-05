/* 
ANUBIS: graph total dataset
Written by Joseph Farah on August 30, 2017
Last updated by [Joseph Farah] on: [September 4th, 2017]

Notes
- 
*/

// header imports
#include <iostream>
#include <vector>
#include <sstream>
#include <fstream>
#include <typeinfo>
#include <algorithm>
#include <chrono>
#include <string>
#include <TROOT.h>
#include <TChain.h>
#include <TFile.h>
#include "TSystem.h"
#include "TMath.h"
#include "TH1D.h"
#include "TRandom3.h"
#include "TRandom.h"
#include "TCanvas.h"
#include "TGraph.h"
#include "TApplication.h"

#define TRUE 1
#define FALSE 0

#define pass ;

std::vector<std::string> explode(const std::string& str, const char& ch) {

    /* This function explodes a string into a vector, like split() in python*/

    std::string next;
    std::vector<std::string> result;

    // For each character in the string
    for (std::string::const_iterator it = str.begin(); it != str.end(); it++) {
        // If we've hit the terminal character
        if (*it == ch) {
            // If we have some characters accumulated
            if (!next.empty()) {
                // Add them to the result vector
                result.push_back(next);
                next.clear();
            }
        } else {
            // Accumulate the next character into the sequence
            next += *it;
        }
    }
    if (!next.empty())
        result.push_back(next);
    return result;
}

void progress(double time_diff, int nprocessed, int ntotal){

    /*Alex's progress bar; C implentation*/

    double rate = (double)(nprocessed+1)/time_diff;
    std::cout.precision(1);
    std::cout << "\r > " << nprocessed << " / " << ntotal 
    << " | "   << std::fixed << 100*(double)(nprocessed)/(double)(ntotal) << "%"
    << " | "   << std::fixed << rate << "Hz"
    << " | "   << std::fixed << time_diff/60 << "m elapsed"
    << " | "   << std::fixed << (double)(ntotal-nprocessed)/(rate*60) << "m remaining"
    << std::flush;
    std::cout.precision(6);
}


int main( int argc, char *argv[] )
{
	/* check that all necessary arguments have been provided */
	if(argc != 2) { std::cout << "Please provide a database file." << std::endl; return 0;}
	
	/* timer stuff */
	std::chrono::time_point<std::chrono::system_clock> time_start;
    std::chrono::duration<double> elapsed_seconds;
    time_start = std::chrono::system_clock::now();
    
    /* create the database file name */
    const char* database_file = argv[1];

    /* create a new app and canvas */
    // TApplication app("app", nullptr, nullptr);
    TCanvas *canvas = new TCanvas("c1", "testing");
    canvas->SetWindowSize(900, 600);
    canvas->Divide(1,1);


    /* Prepare necessary variables for file analysis*/
    std::vector<std::string>    exploded_line;
    std::string                 line;
    std::ifstream               db_file;
    int num_of_lines = 0;

    /* get number of lines in the file */
    std::ifstream f(database_file);
	std::string ln;
    for (num_of_lines = 0; std::getline(f, ln); ++num_of_lines) { pass }
    std::cout << num_of_lines << std::endl;
    

    /* open the database file */
    db_file.open(database_file);

    /* define some necessary vars */
    int         i;
    int         line_num = 0;
    double      x_val, y_val, hr, sc;
    double t[num_of_lines], v[num_of_lines];

    /* check if the file is openable, if it is grab the data*/
    if(db_file.is_open())
    {
    	/* while there is a new line to be grabbed */
        while(getline(db_file, line))
        {   
            std::stringstream ss(line);
            /*line.erase(0,1);*/
            line.erase(line.size()-1);
            exploded_line = explode(line, ',');

            t[line_num] = line_num;
            v[line_num] = std::stod(exploded_line[0]);

            if(line_num%50==0) {    
                elapsed_seconds = (std::chrono::system_clock::now() - time_start);
                progress(elapsed_seconds.count(), line_num, num_of_lines);
            }
            line_num++;
        }
    }
    TGraph *gr = new TGraph(num_of_lines,t,v);
    gr->SetTitle("Voltage vs time");
    gr->GetXaxis()->SetTitle("Time since the start of the run (seconds)");
    gr->GetYaxis()->SetTitle("Voltage (volts)");
    gr->Draw("");
    canvas->Update();
    canvas->SaveAs("total_realtime.pdf");




    // app.Run();
    return 0;
}