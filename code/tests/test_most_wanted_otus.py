#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012, The QIIME project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPL"
__version__ = "1.5.0-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"
__status__ = "Development"

"""Test suite for the most_wanted_otus.py module."""

from os import makedirs, getcwd, chdir
from os.path import basename, exists, join, normpath
from shutil import rmtree
from tempfile import mkdtemp, NamedTemporaryFile

from numpy import array

from biom.table import table_factory, SparseOTUTable
from cogent.app.formatdb import build_blast_db_from_fasta_path
from cogent.util.misc import remove_files
from cogent.util.unit_test import TestCase, main
from qiime.test import initiate_timeout, disable_timeout
from qiime.util import get_qiime_temp_dir, get_tmp_filename
from qiime.workflow.util import WorkflowError

from emp.most_wanted_otus import (generate_most_wanted_list,
        _get_most_wanted_filtering_commands, _get_top_n_blast_results,
        _get_rep_set_lookup, _format_top_n_results_table,
        _format_pie_chart_data, _format_legend_html)

class MostWantedOtusTests(TestCase):
    """Tests for the most_wanted_otus.py module."""

    def setUp(self):
        """Set up files/environment that will be used by the tests."""
        # The prefix to use for temporary files. This prefix may be added to,
        # but all temp dirs and files created by the tests will have this
        # prefix at a minimum.
        self.prefix = 'most_wanted_otus_tests_'
        self.files_to_remove = []
        self.dirs_to_remove = []

        self.output_dir = mkdtemp(prefix='%soutput_dir_' % self.prefix)
        self.dirs_to_remove.append(self.output_dir)

        self.grouping_category = 'Environment'
        self.top_n = 100

        self.blast_results_lines = blast_results.split('\n')
        self.blast_results_dupes_lines = blast_results_dupes.split('\n')
        self.rep_set_lines = rep_set.split('\n')
        self.top_n_mw = [('a', 'gi|7|emb|T51700.1|', 87.0),
                         ('b', 'gi|8|emb|Z700.1|', 89.5)]
        self.mw_seqs = {'b':'AAGGTT', 'a':'AGT'}
        self.master_otu_table_ms = table_factory(
                array([[1.0, 2.0], [2.0, 5.0]]), ['Env1', 'Env2'], ['a', 'b'],
                sample_metadata=None,
                observation_metadata=[{'taxonomy':'foo;bar;baz'},
                {'taxonomy':'foo;baz;bar'}], table_id=None,
                constructor=SparseOTUTable)

    def tearDown(self):
        """Remove temporary files/dirs."""
        remove_files(self.files_to_remove)
        # remove directories last, so we don't get errors
        # trying to remove files which may be in the directories
        for d in self.dirs_to_remove:
            if exists(d):
                rmtree(d)

    def test_get_most_wanted_filtering_commands(self):
        obs = _get_most_wanted_filtering_commands('/foo', ['/a.biom',
                '/b.biom', '/c.biom'], '/rs.fna', '/gg.fasta', '/nt',
                '/map.txt', 'Env', 30, 100, 5, 0.70, 1e-4, 25, None, 55)
        self.assertEqual(obs, exp_commands)

    def test_get_most_wanted_filtering_commands_merged_master_otu_table(self):
        obs = _get_most_wanted_filtering_commands('/foo', ['/a.biom',
                '/b.biom', '/c.biom'], '/rs.fna', '/gg.fasta', '/nt',
                '/map.txt', 'Env', 30, 100, 5, 0.70, 1e-4, 25, '/master.biom',
                55)
        self.assertEqual(obs, exp_commands_merged_master_otu_table)

    def test_get_top_n_blast_results(self):
        exp = [('New.CleanUp.ReferenceOTU969', 'gi|16|emb|Z52700.1|', 90.0),
                ('New.CleanUp.ReferenceOTU999', 'gi|7|emb|X51700.1|', 100.0),
                ('New.CleanUp.ReferenceOTU972', 'gi|7|emb|T51700.1|', 100.0)]
        obs = _get_top_n_blast_results(self.blast_results_lines, self.top_n,
                                       1.0)
        self.assertFloatEqual(obs, exp)

    def test_get_top_n_blast_results_max_nt_similarity(self):
        exp = [('New.CleanUp.ReferenceOTU969', 'gi|16|emb|Z52700.1|', 90.0)]
        obs = _get_top_n_blast_results(self.blast_results_lines, self.top_n,
                                       0.97)
        self.assertFloatEqual(obs, exp)

        obs = _get_top_n_blast_results(self.blast_results_lines, self.top_n,
                                       0.90)
        self.assertFloatEqual(obs, exp)

    def test_get_top_n_blast_results_duplicate_blast_hits(self):
        exp = [('New.CleanUp.ReferenceOTU969', 'gi|16|emb|Z52700.1|', 90.0),
               ('New.CleanUp.ReferenceOTU972', 'gi|7|emb|T51700.1|', 95.0)]
        obs = _get_top_n_blast_results(self.blast_results_dupes_lines,
                                       2, 1.0)
        self.assertFloatEqual(obs, exp)

    def test_get_rep_set_lookup(self):
        obs = _get_rep_set_lookup(self.rep_set_lines)
        self.assertEqual(obs, exp_rep_set_lookup)

    def test_format_top_n_results_table(self):
        obs = _format_top_n_results_table(self.top_n_mw, self.mw_seqs,
                self.master_otu_table_ms, self.output_dir,
                self.grouping_category, False, 8)

        obs_plot_paths = [fp.replace(self.output_dir, 'foo') for fp in obs[3]]
        obs_plot_data_paths = [fp.replace(self.output_dir, 'foo')
                               for fp in obs[4]]
        obs = (obs[0],
               obs[1].replace(basename(normpath(self.output_dir)), 'foo'),
               obs[2],
               obs_plot_paths,
               obs_plot_data_paths)
        self.assertEqual(obs, exp_output_tables)

    def test_format_top_n_results_table_suppress_taxonomy(self):
        obs = _format_top_n_results_table(self.top_n_mw, self.mw_seqs,
                self.master_otu_table_ms, self.output_dir,
                self.grouping_category, True, 8)

        obs_plot_paths = [fp.replace(self.output_dir, 'foo') for fp in obs[3]]
        obs_plot_data_paths = [fp.replace(self.output_dir, 'foo')
                               for fp in obs[4]]
        obs = (obs[0],
               obs[1].replace(basename(normpath(self.output_dir)), 'foo'),
               obs[2],
               obs_plot_paths,
               obs_plot_data_paths)
        self.assertEqual(obs, exp_output_tables_suppressed_taxonomy)

    def test_format_pie_chart_data(self):
        exp = ([0.6666666666666666, 0.3333333333333333],
               ['b (66.67%)', 'a (33.33%)'], ['#0000ff', '#ff0000'])
        obs = _format_pie_chart_data(['a', 'b'], [1, 2], 2)
        self.assertFloatEqual(obs, exp)

        obs = _format_pie_chart_data(['a', 'b'], [1.0, 2.0], 3)
        self.assertFloatEqual(obs, exp)

    def test_format_pie_chart_data_max_count(self):
        exp = ([1.0], ['b (100.00%)'], ['#0000ff'])
        obs = _format_pie_chart_data(['a', 'b'], [1, 2], 1)
        self.assertFloatEqual(obs, exp)

    def test_format_pie_chart_data_cycle_colors(self):
        exp = ([0.5, 0.5], ['a (50.00%)', '4 (50.00%)'],
               ['#ff0000', '#ff0000'])
        obs = _format_pie_chart_data(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h',
            'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
            'v', 'w', 'x', 'y', 'z', '1', '2', '3', '4'],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 1], 2)
        self.assertFloatEqual(obs, exp)

    def test_format_legend_html(self):
        exp = ('<ul class="most_wanted_otus_legend"><li><div class="key" style="background-color:#0000ff"></div>b (66.67%)</li><li><div class="key" style="background-color:#ff0000"></div>a (33.33%)</li>'
            '</ul>')
        obs = _format_legend_html(([0.6666666666666666, 0.3333333333333333],
               ['b (66.67%)', 'a (33.33%)'], ['#0000ff', '#ff0000']))
        self.assertEqual(obs, exp)


rep_set = """
>New.CleanUp.ReferenceOTU999 S1_18210
ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGATGTTTAAGTGGGATGTGAAATCCCCGGGCTTAACCTGGGGGCTGC
>10113 S1_88960
ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGCGCACGCAGGCGGTCTGTTAAGTCAGATGTGAAATCCCCGGGCTCCACCTGGGCACTGC
>10115 S2_9552
ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGCGCACGCAGGCGGTTTGTTAAGTTTGATGTGAAATCCCCGGGCTTAACCTGGGAACTGC
>102506 S1_46428
ATACGTATGGTGCAAGCGTTATCCGGATTTACTGGGTGTAAAGGGAGCGCAGGCGGTACGGCAAGTCTGATGTGAAAGTCCGGGGCTCAACCCCGGTACTGC
AAACGTAGGGTGCAAGCGTTGTCCGGAATTACTGGGTGTAAAGGGAGCGTAGACGGCTGTGCAAGTCTGAAGTGAAAGGCATGGGCTCAACCTGTGGACTGC
>New.CleanUp.ReferenceOTU964 S2_295794
ATACGGAGGATGCGAGCGTTATCCGGATTTATTGGGTTTAAAGGGTGCGTAGACGGCGAAGCAAGTCTGAAGTGAAAGCCCGGGGCTCAACCGCGGGACTGC
>New.CleanUp.ReferenceOTU969 S2_166346
ATACGTAGGTCCCGAGCGTTGTCCGGATTTACTGGGTGTAAAGGGAGCGTAGACGGCATGGCAAGTCTGAAGTGAAAACCCAGGGCTCAACCCTGGGACTGC
>New.CleanUp.ReferenceOTU972 S1_18219
ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGATGTTTAAGTGGGATGTGAAATCCCCGGGCTTAACCTGGGGGCTGC
"""

blast_results = """
# BLASTN 2.2.22 [Sep-27-2009]
# Query: New.CleanUp.ReferenceOTU999
# Database: small_nt
# Fields: Query id, Subject id, % identity, alignment length, mismatches, gap openings, q. start, q. end, s. start, s. end, e-value, bit score
New.CleanUp.ReferenceOTU999	gi|7|emb|X51700.1|	100.00	11	0	0	92	102	367	357	0.25	22.3
# BLASTN 2.2.22 [Sep-27-2009]
# Query: New.CleanUp.ReferenceOTU972
# Database: small_nt
# Fields: Query id, Subject id, % identity, alignment length, mismatches, gap openings, q. start, q. end, s. start, s. end, e-value, bit score
New.CleanUp.ReferenceOTU972	gi|7|emb|T51700.1|	100.00	11	0	0	92	102	367	357	0.25	22.3
# BLASTN 2.2.22 [Sep-27-2009]
# Query: New.CleanUp.ReferenceOTU969
# Database: small_nt
# Fields: Query id, Subject id, % identity, alignment length, mismatches, gap openings, q. start, q. end, s. start, s. end, e-value, bit score
New.CleanUp.ReferenceOTU969	gi|16|emb|Z52700.1|	90.00	13	0	0	33	45	1604	1616	0.016	26.3
"""

blast_results_dupes = """
# BLASTN 2.2.22 [Sep-27-2009]
# Query: New.CleanUp.ReferenceOTU999
# Database: small_nt
# Fields: Query id, Subject id, % identity, alignment length, mismatches, gap openings, q. start, q. end, s. start, s. end, e-value, bit score
New.CleanUp.ReferenceOTU999	gi|7|emb|X51700.1|	100.00	11	0	0	92	102	367	357	0.25	22.3
# BLASTN 2.2.22 [Sep-27-2009]
# Query: New.CleanUp.ReferenceOTU972
# Database: small_nt
# Fields: Query id, Subject id, % identity, alignment length, mismatches, gap openings, q. start, q. end, s. start, s. end, e-value, bit score
New.CleanUp.ReferenceOTU972	gi|7|emb|T51700.1|	95.00	11	0	0	92	102	367	357	0.25	22.3
New.CleanUp.ReferenceOTU972	gi|7|emb|T51700.1|	95.00	11	0	0	92	102	367	357	0.27	22.3
# BLASTN 2.2.22 [Sep-27-2009]
# Query: New.CleanUp.ReferenceOTU969
# Database: small_nt
# Fields: Query id, Subject id, % identity, alignment length, mismatches, gap openings, q. start, q. end, s. start, s. end, e-value, bit score
New.CleanUp.ReferenceOTU969	gi|16|emb|Z52700.1|	90.00	13	0	0	33	45	1604	1616	0.016	26.3
"""

exp_txt = """OTU ID	Sequence	Taxonomy	NCBI nr closest match
New.CleanUp.ReferenceOTU972	ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGATGTTTAAGTGGGATGTGAAATCCCCGGGCTTAACCTGGGGGCTGC	foo;bar;baz	http://foo.com
New.CleanUp.ReferenceOTU969	ATACGTAGGTCCCGAGCGTTGTCCGGATTTACTGGGTGTAAAGGGAGCGTAGACGGCATGGCAAGTCTGAAGTGAAAACCCAGGGCTCAACCCTGGGACTGC	foo;bar;baz	http://foo.com
New.CleanUp.ReferenceOTU964	ATACGGAGGATGCGAGCGTTATCCGGATTTATTGGGTTTAAAGGGTGCGTAGACGGCGAAGCAAGTCTGAAGTGAAAGCCCGGGGCTCAACCGCGGGACTGC	foo;bar;baz	http://foo.com
New.CleanUp.ReferenceOTU999	ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGATGTTTAAGTGGGATGTGAAATCCCCGGGCTTAACCTGGGGGCTGC	foo;bar;bazz	http://foo.com
"""

exp_commands = ([[('Filtering out all GG reference OTUs', 'filter_otus_from_otu_table.py -i /a.biom -o /foo/a_novel.biom -e /gg.fasta')], [('Filtering out all OTUs that do not fall within the specified abundance threshold', 'filter_otus_from_otu_table.py -i /foo/a_novel.biom -o /foo/a_novel_min30_max100.biom -n 30 -x 100')], [('Filtering out samples that are not in the mapping file', 'filter_samples_from_otu_table.py -i /foo/a_novel_min30_max100.biom -o /foo/a_novel_min30_max100_known_samples.biom --sample_id_fp /map.txt')], [('Collapsing OTU table by Env', 'summarize_otu_by_cat.py -c /foo/a_novel_min30_max100_known_samples.biom -o /foo/a_novel_min30_max100_known_samples_Env.biom -m Env -i /map.txt')], [('Filtering out all GG reference OTUs', 'filter_otus_from_otu_table.py -i /b.biom -o /foo/b_novel.biom -e /gg.fasta')], [('Filtering out all OTUs that do not fall within the specified abundance threshold', 'filter_otus_from_otu_table.py -i /foo/b_novel.biom -o /foo/b_novel_min30_max100.biom -n 30 -x 100')], [('Filtering out samples that are not in the mapping file', 'filter_samples_from_otu_table.py -i /foo/b_novel_min30_max100.biom -o /foo/b_novel_min30_max100_known_samples.biom --sample_id_fp /map.txt')],[('Collapsing OTU table by Env', 'summarize_otu_by_cat.py -c /foo/b_novel_min30_max100_known_samples.biom -o /foo/b_novel_min30_max100_known_samples_Env.biom -m Env -i /map.txt')], [('Filtering out all GG reference OTUs', 'filter_otus_from_otu_table.py -i /c.biom -o /foo/c_novel.biom -e /gg.fasta')], [('Filtering out all OTUs that do not fall within the specified abundance threshold', 'filter_otus_from_otu_table.py -i /foo/c_novel.biom -o /foo/c_novel_min30_max100.biom -n 30 -x 100')], [('Filtering out samples that are not in the mapping file', 'filter_samples_from_otu_table.py -i /foo/c_novel_min30_max100.biom -o /foo/c_novel_min30_max100_known_samples.biom --sample_id_fp /map.txt')], [('Collapsing OTU table by Env', 'summarize_otu_by_cat.py -c /foo/c_novel_min30_max100_known_samples.biom -o /foo/c_novel_min30_max100_known_samples_Env.biom -m Env -i /map.txt')], [('Merging collapsed OTU tables', 'merge_otu_tables.py -i /foo/a_novel_min30_max100_known_samples_Env.biom,/foo/b_novel_min30_max100_known_samples_Env.biom,/foo/c_novel_min30_max100_known_samples_Env.biom -o /foo/master_otu_table_novel_min30_max100_Env.biom')], [('Filtering OTU table to include only OTUs that appear in at least 5 sample groups', 'filter_otus_from_otu_table.py -i /foo/master_otu_table_novel_min30_max100_Env.biom -o /foo/master_otu_table_novel_min30_max100_Env_ms5.biom -s 5')], [('Filtering representative set to include only the latest candidate OTUs', 'filter_fasta.py -f /rs.fna -o /foo/rs_candidates.fna -b /foo/master_otu_table_novel_min30_max100_Env_ms5.biom')], [("Running uclust to get list of sequences that don't hit the maximum GG similarity threshold", 'parallel_pick_otus_uclust_ref.py -i /foo/rs_candidates.fna -o /foo/most_wanted_candidates_gg.fasta_0.7 -r /gg.fasta -s 0.7 -O 55')], [('Filtering candidate sequences to only include uclust failures', 'filter_fasta.py -f /foo/rs_candidates.fna -s /foo/most_wanted_candidates_gg.fasta_0.7/rs_candidates_failures.txt -o /foo/rs_candidates_failures.fna')], [('BLASTing filtered candidate sequences against nt database', 'parallel_blast.py -i /foo/rs_candidates_failures.fna -o /foo/blast_output -r /nt -D -e 0.000100 -w 25 -O 55')]], '/foo/blast_output/rs_candidates_failures_blast_out.txt', '/foo/rs_candidates_failures.fna', '/foo/master_otu_table_novel_min30_max100_Env_ms5.biom')

exp_commands_merged_master_otu_table = ([[('Filtering OTU table to include only OTUs that appear in at least 5 sample groups', 'filter_otus_from_otu_table.py -i /master.biom -o /foo/master_ms5.biom -s 5')], [('Filtering representative set to include only the latest candidate OTUs', 'filter_fasta.py -f /rs.fna -o /foo/rs_candidates.fna -b /foo/master_ms5.biom')], [("Running uclust to get list of sequences that don't hit the maximum GG similarity threshold", 'parallel_pick_otus_uclust_ref.py -i /foo/rs_candidates.fna -o /foo/most_wanted_candidates_gg.fasta_0.7 -r /gg.fasta -s 0.7 -O 55')], [('Filtering candidate sequences to only include uclust failures', 'filter_fasta.py -f /foo/rs_candidates.fna -s /foo/most_wanted_candidates_gg.fasta_0.7/rs_candidates_failures.txt -o /foo/rs_candidates_failures.fna')], [('BLASTing filtered candidate sequences against nt database', 'parallel_blast.py -i /foo/rs_candidates_failures.fna -o /foo/blast_output -r /nt -D -e 0.000100 -w 25 -O 55')]], '/foo/blast_output/rs_candidates_failures_blast_out.txt', '/foo/rs_candidates_failures.fna', '/foo/master_ms5.biom')

exp_rep_set_lookup = {'New.CleanUp.ReferenceOTU999': 'ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGATGTTTAAGTGGGATGTGAAATCCCCGGGCTTAACCTGGGGGCTGC', '102506': 'ATACGTATGGTGCAAGCGTTATCCGGATTTACTGGGTGTAAAGGGAGCGCAGGCGGTACGGCAAGTCTGATGTGAAAGTCCGGGGCTCAACCCCGGTACTGCAAACGTAGGGTGCAAGCGTTGTCCGGAATTACTGGGTGTAAAGGGAGCGTAGACGGCTGTGCAAGTCTGAAGTGAAAGGCATGGGCTCAACCTGTGGACTGC', 'New.CleanUp.ReferenceOTU972': 'ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGATGTTTAAGTGGGATGTGAAATCCCCGGGCTTAACCTGGGGGCTGC', 'New.CleanUp.ReferenceOTU969': 'ATACGTAGGTCCCGAGCGTTGTCCGGATTTACTGGGTGTAAAGGGAGCGTAGACGGCATGGCAAGTCTGAAGTGAAAACCCAGGGCTCAACCCTGGGACTGC', 'New.CleanUp.ReferenceOTU964': 'ATACGGAGGATGCGAGCGTTATCCGGATTTATTGGGTTTAAAGGGTGCGTAGACGGCGAAGCAAGTCTGAAGTGAAAGCCCGGGGCTCAACCGCGGGACTGC', '10115': 'ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGCGCACGCAGGCGGTTTGTTAAGTTTGATGTGAAATCCCCGGGCTTAACCTGGGAACTGC', '10113': 'ATACGGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGCGCACGCAGGCGGTCTGTTAAGTCAGATGTGAAATCCCCGGGCTCCACCTGGGCACTGC'}

exp_output_tables = ('#\tOTU ID\tSequence\tGreengenes taxonomy\tNCBI nt closest match\tNCBI nt % identity\n1\ta\tAGT\tfoo;bar;baz\tT51700.1\t87.0\n2\tb\tAAGGTT\tfoo;baz;bar\tZ700.1\t89.5\n', '<table id="most_wanted_otus_table" border="border"><tr><th>#</th><th>OTU</th><th>Greengenes taxonomy</th><th>NCBI nt closest match</th><th>Abundance by Environment</th></tr><tr><td>1</td><td><pre>&gt;a\nAGT</pre></td><td>foo;bar;baz</td><td><a href="http://www.ncbi.nlm.nih.gov/nuccore/T51700.1" target="_blank">T51700.1</a> (87.0% sim.)</td><td><table><tr><td><img src="foo/abundance_by_Environment_a.png" width="300" height="300" /></td><td><ul class="most_wanted_otus_legend"><li><div class="key" style="background-color:#0000ff"></div>Env2 (66.67%)</li><li><div class="key" style="background-color:#ff0000"></div>Env1 (33.33%)</li></ul></td></tr></table></tr><tr><td>2</td><td><pre>&gt;b\nAAGGTT</pre></td><td>foo;baz;bar</td><td><a href="http://www.ncbi.nlm.nih.gov/nuccore/Z700.1" target="_blank">Z700.1</a> (89.5% sim.)</td><td><table><tr><td><img src="foo/abundance_by_Environment_b.png" width="300" height="300" /></td><td><ul class="most_wanted_otus_legend"><li><div class="key" style="background-color:#0000ff"></div>Env2 (71.43%)</li><li><div class="key" style="background-color:#ff0000"></div>Env1 (28.57%)</li></ul></td></tr></table></tr></table>', '>a\nAGT\n>b\nAAGGTT\n', ['foo/abundance_by_Environment_a.png', 'foo/abundance_by_Environment_b.png'], ['foo/abundance_by_Environment_a.p', 'foo/abundance_by_Environment_b.p'])

exp_output_tables_suppressed_taxonomy = ('#\tOTU ID\tSequence\tNCBI nt closest match\tNCBI nt % identity\n1\ta\tAGT\tT51700.1\t87.0\n2\tb\tAAGGTT\tZ700.1\t89.5\n', '<table id="most_wanted_otus_table" border="border"><tr><th>#</th><th>OTU</th><th>NCBI nt closest match</th><th>Abundance by Environment</th></tr><tr><td>1</td><td><pre>&gt;a\nAGT</pre></td><td><a href="http://www.ncbi.nlm.nih.gov/nuccore/T51700.1" target="_blank">T51700.1</a> (87.0% sim.)</td><td><table><tr><td><img src="foo/abundance_by_Environment_a.png" width="300" height="300" /></td><td><ul class="most_wanted_otus_legend"><li><div class="key" style="background-color:#0000ff"></div>Env2 (66.67%)</li><li><div class="key" style="background-color:#ff0000"></div>Env1 (33.33%)</li></ul></td></tr></table></tr><tr><td>2</td><td><pre>&gt;b\nAAGGTT</pre></td><td><a href="http://www.ncbi.nlm.nih.gov/nuccore/Z700.1" target="_blank">Z700.1</a> (89.5% sim.)</td><td><table><tr><td><img src="foo/abundance_by_Environment_b.png" width="300" height="300" /></td><td><ul class="most_wanted_otus_legend"><li><div class="key" style="background-color:#0000ff"></div>Env2 (71.43%)</li><li><div class="key" style="background-color:#ff0000"></div>Env1 (28.57%)</li></ul></td></tr></table></tr></table>', '>a\nAGT\n>b\nAAGGTT\n', ['foo/abundance_by_Environment_a.png', 'foo/abundance_by_Environment_b.png'], ['foo/abundance_by_Environment_a.p', 'foo/abundance_by_Environment_b.p'])

if __name__ == "__main__":
    main()
