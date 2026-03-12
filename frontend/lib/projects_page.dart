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
      body: errorMessage.isNotEmpty
          ? Center(child: Text(errorMessage))
          : ListView.builder(
              itemCount: projects.length,
              itemBuilder: (context, index) {
                final project = projects[index];
                return ListTile(
                  title: Text(project['name']),
                  subtitle: Text('ID: ${project['id']}'),
                );
              },
            ),
    );
  }
}