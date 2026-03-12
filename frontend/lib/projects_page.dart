import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class ProjectsPage extends StatefulWidget {
  const ProjectsPage({super.key});

  @override
  State<ProjectsPage> createState() => _ProjectsPageState();
}

class _ProjectsPageState extends State<ProjectsPage> {
  List<dynamic> projects = [];
  String errorMessage = '';
  final TextEditingController nameController = TextEditingController();

  Future<void> loadProjects() async {
    try {
      final url = Uri.parse('http://127.0.0.1:8000/projects');
      final response = await http.get(url);
      final data = jsonDecode(response.body);

      setState(() {
        projects = data;
        errorMessage = '';
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
      });
    }
  }

  Future<void> createProject() async {
    try {
      final name = nameController.text.trim();

      if (name.isEmpty) {
        setState(() {
          errorMessage = 'Enter a project name';
        });
        return;
      }

      final url = Uri.parse('http://127.0.0.1:8000/projects/$name');
      final response = await http.post(url);

      if (response.statusCode == 200) {
        nameController.clear();
        await loadProjects();
      } else {
        setState(() {
          errorMessage = 'Failed to create project';
        });
      }
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
      });
    }
  }

  @override
  void initState() {
    super.initState();
    loadProjects();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Projects'),
      ),
      body: Padding(
  padding: const EdgeInsets.all(16),
  child: Column(
    children: [
      TextField(
        controller: nameController,
        decoration: const InputDecoration(
          labelText: 'Project name',
          border: OutlineInputBorder(),
        ),
      ),
      const SizedBox(height: 12),
      ElevatedButton(
        onPressed: createProject,
        child: const Text('Create Project'),
      ),
      const SizedBox(height: 12),
      if (errorMessage.isNotEmpty) Text(errorMessage),
      Expanded(
        child: ListView.builder(
          itemCount: projects.length,
          itemBuilder: (context, index) {
            final project = projects[index];
            return ListTile(
              title: Text(project['name']),
              subtitle: Text('ID: ${project['id']}'),
            );
          },
        ),
      ),
    ],
  ),
),
    );
  }
}