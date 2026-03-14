import 'dart:async';

import 'package:flutter/material.dart';

import 'api/intelliclaw_api.dart';
import 'models.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key, this.api});

  final IntelliclawApi? api;

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final TextEditingController _nameController = TextEditingController();

  List<Project> _projects = const [];
  ProjectSummary _summary = const ProjectSummary(projectCount: 0, documentCount: 0);
  bool _isLoading = true;
  bool _isSaving = false;
  bool _backendOnline = false;
  String _errorMessage = '';

  late final IntelliclawApi _api;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? IntelliclawApi();
    unawaited(_loadDashboard());
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _loadDashboard() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final backendOnline = await _api.healthCheck();
      final summary = await _api.fetchSummary();
      final projects = await _api.fetchProjects();

      if (!mounted) {
        return;
      }

      setState(() {
        _backendOnline = backendOnline;
        _summary = summary;
        _projects = projects;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _backendOnline = false;
        _isLoading = false;
        _errorMessage = error.toString();
      });
    }
  }

  Future<void> _createProject() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      setState(() {
        _errorMessage = 'Enter a project name before creating it.';
      });
      return;
    }

    setState(() {
      _isSaving = true;
      _errorMessage = '';
    });

    try {
      await _api.createProject(name);
      _nameController.clear();
      await _loadDashboard();
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
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFEAF1FF), Color(0xFFF8FBFF)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1200),
              child: RefreshIndicator(
                onRefresh: _loadDashboard,
                child: ListView(
                  padding: const EdgeInsets.all(24),
                  children: [
                    Wrap(
                      spacing: 24,
                      runSpacing: 24,
                      alignment: WrapAlignment.spaceBetween,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        SizedBox(
                          width: 620,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Intelliclaw',
                                style: theme.textTheme.displaySmall?.copyWith(
                                  fontWeight: FontWeight.w700,
                                  color: const Color(0xFF10233D),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                'First web iteration for managing research projects before we plug in the Kaggle document-analysis workflow.',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  color: const Color(0xFF43556F),
                                ),
                              ),
                            ],
                          ),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: _isLoading ? null : _loadDashboard,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Refresh'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        _StatCard(
                          label: 'Backend',
                          value: _backendOnline ? 'Online' : 'Offline',
                          icon: Icons.cloud_done_outlined,
                          accent: _backendOnline
                              ? const Color(0xFF1F8F5F)
                              : const Color(0xFFC15555),
                        ),
                        _StatCard(
                          label: 'Projects',
                          value: '${_summary.projectCount}',
                          icon: Icons.folder_open_outlined,
                          accent: const Color(0xFF0B5FFF),
                        ),
                        _StatCard(
                          label: 'Documents',
                          value: '${_summary.documentCount}',
                          icon: Icons.description_outlined,
                          accent: const Color(0xFF7A58D1),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Wrap(
                      spacing: 24,
                      runSpacing: 24,
                      crossAxisAlignment: WrapCrossAlignment.start,
                      children: [
                        SizedBox(
                          width: 360,
                          child: _CreateProjectCard(
                            controller: _nameController,
                            isSaving: _isSaving,
                            onSubmit: _createProject,
                            errorMessage: _errorMessage,
                          ),
                        ),
                        SizedBox(
                          width: 780,
                          child: _ProjectsCard(
                            isLoading: _isLoading,
                            projects: _projects,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    const _RoadmapCard(),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 250,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: const [
          BoxShadow(
            color: Color(0x140E203A),
            blurRadius: 24,
            offset: Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            backgroundColor: accent.withOpacity(0.12),
            foregroundColor: accent,
            child: Icon(icon),
          ),
          const SizedBox(height: 18),
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: const Color(0xFF10233D),
                ),
          ),
        ],
      ),
    );
  }
}

class _CreateProjectCard extends StatelessWidget {
  const _CreateProjectCard({
    required this.controller,
    required this.isSaving,
    required this.onSubmit,
    required this.errorMessage,
  });

  final TextEditingController controller;
  final bool isSaving;
  final Future<void> Function() onSubmit;
  final String errorMessage;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: _cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Create research project',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Use projects to group future uploads, extracted tables, and analysis runs.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),
          TextField(
            controller: controller,
            decoration: const InputDecoration(
              labelText: 'Project name',
              border: OutlineInputBorder(),
            ),
            onSubmitted: (_) => onSubmit(),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: isSaving ? null : onSubmit,
              icon: isSaving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.add),
              label: Text(isSaving ? 'Creating...' : 'Create project'),
            ),
          ),
          if (errorMessage.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              errorMessage,
              style: TextStyle(
                color: Theme.of(context).colorScheme.error,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ProjectsCard extends StatelessWidget {
  const _ProjectsCard({
    required this.isLoading,
    required this.projects,
  });

  final bool isLoading;
  final List<Project> projects;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: _cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Project inventory',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'This is the current system of record for the first iteration.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),
          if (isLoading)
            const Center(child: CircularProgressIndicator())
          else if (projects.isEmpty)
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                color: const Color(0xFFF5F8FC),
              ),
              child: const Text('No projects yet. Create the first one to get started.'),
            )
          else
            ...projects.map(
              (project) => Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  color: const Color(0xFFF9FBFF),
                  border: Border.all(color: const Color(0xFFE1E8F3)),
                ),
                child: Row(
                  children: [
                    const CircleAvatar(
                      backgroundColor: Color(0xFFE4ECFF),
                      foregroundColor: Color(0xFF0B5FFF),
                      child: Icon(Icons.folder_outlined),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            project.name,
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                          const SizedBox(height: 4),
                          Text('Project #${project.id}'),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '${project.documentCount} documents',
                          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                color: const Color(0xFF43556F),
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          project.createdAt,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _RoadmapCard extends StatelessWidget {
  const _RoadmapCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: _cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Next integration milestone',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 12),
          const Text(
            'The Kaggle notebook already defines the future analysis direction: upload product PDFs, extract tables, unify them, normalize features, and generate a gaps matrix. The next backend iteration should turn that notebook flow into API jobs that belong to a project.',
          ),
        ],
      ),
    );
  }
}

BoxDecoration _cardDecoration() {
  return BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(28),
    boxShadow: const [
      BoxShadow(
        color: Color(0x140E203A),
        blurRadius: 24,
        offset: Offset(0, 12),
      ),
    ],
  );
}
