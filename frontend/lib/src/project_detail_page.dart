import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import 'api/intelliclaw_api.dart';
import 'models.dart';

class ProjectDetailPage extends StatefulWidget {
  const ProjectDetailPage({
    required this.projectId,
    required this.api,
    super.key,
  });

  final int projectId;
  final IntelliclawApi api;

  @override
  State<ProjectDetailPage> createState() => _ProjectDetailPageState();
}

class _ProjectDetailPageState extends State<ProjectDetailPage> {
  ProjectDetail? _projectDetail;
  bool _isLoading = true;
  bool _isUploading = false;
  bool _isRunningAnalysis = false;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadProject();
  }

  Future<void> _loadProject() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final detail = await widget.api.fetchProjectDetail(widget.projectId);
      if (!mounted) {
        return;
      }

      setState(() {
        _projectDetail = detail;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = error.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _pickAndUploadDocument() async {
    setState(() {
      _isUploading = true;
      _errorMessage = '';
    });

    try {
      final result = await FilePicker.platform.pickFiles(
        withData: true,
        type: FileType.custom,
        allowedExtensions: ['pdf'],
      );

      if (result == null || result.files.isEmpty) {
        return;
      }

      final file = result.files.single;
      final bytes = file.bytes;
      if (bytes == null) {
        throw Exception('Unable to read selected file bytes.');
      }

      await widget.api.uploadDocument(
        projectId: widget.projectId,
        filename: file.name,
        bytes: bytes,
      );
      await _loadProject();
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  Future<void> _runAnalysis() async {
    setState(() {
      _isRunningAnalysis = true;
      _errorMessage = '';
    });

    try {
      await widget.api.createAnalysisRun(projectId: widget.projectId);
      await _loadProject();
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isRunningAnalysis = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = _projectDetail;

    return Scaffold(
      appBar: AppBar(
        title: Text(detail?.project.name ?? 'Project'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : detail == null
              ? Center(child: Text(_errorMessage.isEmpty ? 'Project not found.' : _errorMessage))
              : ListView(
                  padding: const EdgeInsets.all(24),
                  children: [
                    Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        _MetricCard(
                          label: 'Project',
                          value: detail.project.name,
                        ),
                        _MetricCard(
                          label: 'Documents',
                          value: '${detail.documents.length}',
                        ),
                        _MetricCard(
                          label: 'Analysis runs',
                          value: '${detail.analysisRuns.length}',
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        FilledButton.icon(
                          onPressed: _isUploading ? null : _pickAndUploadDocument,
                          icon: _isUploading
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.upload_file),
                          label: Text(_isUploading ? 'Uploading...' : 'Upload PDF'),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: _isRunningAnalysis ? null : _runAnalysis,
                          icon: _isRunningAnalysis
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.play_arrow),
                          label: Text(
                            _isRunningAnalysis ? 'Running analysis...' : 'Run analysis',
                          ),
                        ),
                        OutlinedButton.icon(
                          onPressed: _loadProject,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Refresh'),
                        ),
                      ],
                    ),
                    if (_errorMessage.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      Text(
                        _errorMessage,
                        style: TextStyle(color: Theme.of(context).colorScheme.error),
                      ),
                    ],
                    const SizedBox(height: 24),
                    _SectionCard(
                      title: 'Documents',
                      subtitle: 'Uploaded competitor PDFs attached to this project.',
                      child: detail.documents.isEmpty
                          ? const Text('No documents uploaded yet.')
                          : Column(
                              children: detail.documents
                                  .map(
                                    (document) => ListTile(
                                      contentPadding: EdgeInsets.zero,
                                      leading: const Icon(Icons.picture_as_pdf_outlined),
                                      title: Text(document.filename),
                                      subtitle: Text(
                                        '${document.status} | ${document.sizeBytes ?? 0} bytes',
                                      ),
                                    ),
                                  )
                                  .toList(),
                            ),
                    ),
                    const SizedBox(height: 24),
                    _SectionCard(
                      title: 'Analysis runs',
                      subtitle: 'Root orchestration plus step-by-step sub-agent results.',
                      child: detail.analysisRuns.isEmpty
                          ? const Text('No analysis runs yet.')
                          : Column(
                              children: detail.analysisRuns
                                  .map(
                                    (run) => Container(
                                      margin: const EdgeInsets.only(bottom: 16),
                                      padding: const EdgeInsets.all(16),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFF8FAFE),
                                        borderRadius: BorderRadius.circular(18),
                                        border: Border.all(color: const Color(0xFFE2E8F2)),
                                      ),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Text(
                                                'Run #${run.id}',
                                                style: Theme.of(context)
                                                    .textTheme
                                                    .titleMedium
                                                    ?.copyWith(fontWeight: FontWeight.w700),
                                              ),
                                              const Spacer(),
                                              _StatusChip(status: run.status),
                                            ],
                                          ),
                                          const SizedBox(height: 8),
                                          if (run.summary != null) Text(run.summary!),
                                          if (run.errorMessage != null)
                                            Text(
                                              run.errorMessage!,
                                              style: TextStyle(
                                                color: Theme.of(context).colorScheme.error,
                                              ),
                                            ),
                                          const SizedBox(height: 12),
                                          Wrap(
                                            spacing: 8,
                                            runSpacing: 8,
                                            children: run.stepResults
                                                .map(
                                                  (step) => Chip(
                                                    label: Text('${step.name}: ${step.status}'),
                                                  ),
                                                )
                                                .toList(),
                                          ),
                                        ],
                                      ),
                                    ),
                                  )
                                  .toList(),
                            ),
                    ),
                  ],
                ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 240,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [
          BoxShadow(
            color: Color(0x120E203A),
            blurRadius: 20,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: const [
          BoxShadow(
            color: Color(0x120E203A),
            blurRadius: 20,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 8),
          Text(subtitle),
          const SizedBox(height: 20),
          child,
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'completed' => const Color(0xFF1F8F5F),
      'failed' => const Color(0xFFC15555),
      'running' => const Color(0xFF0B5FFF),
      _ => const Color(0xFF6C7A90),
    };

    return Chip(
      label: Text(status),
      side: BorderSide(color: color.withOpacity(0.2)),
      backgroundColor: color.withOpacity(0.1),
      labelStyle: TextStyle(
        color: color,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}
