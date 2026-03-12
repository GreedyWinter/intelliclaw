import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'projects_page.dart';

void main() {
  runApp(const IntelliclawApp());
}

class IntelliclawApp extends StatelessWidget {
  const IntelliclawApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Intelliclaw',
      home: const ProjectsPage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String message = 'Press the button to test backend connection';

  Future<void> testBackend() async {
    final url = Uri.parse('http://127.0.0.1:8000/');
    final response = await http.get(url);
    final data = jsonDecode(response.body);

    setState(() {
      message = data['message'];
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Intelliclaw'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text(message),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: testBackend,
              child: const Text('Test Backend'),
            ),
          ],
        ),
      ),
    );
  }
}