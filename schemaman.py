#!/usr/bin/env python
"""
SchemaMan - Schema Manager.  Cross database schema revision control, data migration and data access.

- Manage changes in the schema versions, allowing publication of schemas with your code that is not bound to a single database
    software package or platform.
- Use as a cross-database method of interacting with data (insert/update/delete/get/filter).
- Migrate data between different databases (same or different database software), using rules to update schema, data, or a
    combination.
- Version Management of all data put into the system (unless skipped)
- Change Management of Version Management commits (done through a series of Action scripts, so highly configurable)

Intended for use on smaller data sets, such as those found in System and Network Operational Configuration Management systems.

Copyright Geoff Howland, 2014.  MIT License.
"""


import sys
import os
import getopt
import pprint

# SchemaMan modules
import utility
from utility.log import Log
from utility.error import *
from utility.path import *
import datasource
import action as action_module


# Mode for directories we create.
MODE_DIRECTORY = 0755


def ProcessAction(action, action_args, command_options):
  """Process the specified action, by it's action arguments.  Using command options."""
  
  # If Action is info
  if action == 'info':
    if len(action_args) == 0:
      Usage('"init" action requires 1 argument: path schema definition YAML')
    elif not os.path.isfile(action_args[0]):
      Usage('"init" action requires arguments: %s: Is not a file' % action_args[0])
    
    schema_path = action_args[0]
    
    connection_data = datasource.LoadConnectionSpec(schema_path)
    
    print '\nConnection Specification:\n\n%s\n' % pprint.pformat(connection_data)
    print '\nTesting Connection:\n'
    
    # Attempt to connect to the DB to test it
    result = datasource.TestConnection(connection_data)
    
    if result:
      print '\nConnection test: SUCCESS'
    else:
      print '\nConnection test: FAILURE'
  
  
  # If Action is action:  This is where we dump all kinds of functions, that dont need top-level access.  The long-tail of features.
  elif action == 'action':
    if len(action_args) < 3:
      Usage('"init" action requires at least 3 arguments: <path schema definition YAML> <category> <action>  ...')
    elif not os.path.isfile(action_args[0]):
      Usage('"init" action requires arguments: %s: Is not a file' % action_args[0])
    
    schema_path = action_args[0]
    
    connection_data = datasource.LoadConnectionSpec(schema_path)

    # Get all the args after the initial 3 args and use them as input for our Action function
    action_input_args = action_args[3:]
    
    #TODO(g): Turn this into YAML so that we can add into it.  Make sure it's multiple YAML files or something, so people can add their own without impacting the standard ones
    pass
    
    # Category
    if action_args[1] == 'populate':
      # Action
      if action_args[2] == 'schema_into_db':
        if len(action_input_args) != 1:
          Error('action: populate: schema_into_db: Takes 1 argument: <path to target schema defintion YAML>')
        
        result = action_module.populate.schema_into_db.Action(connection_data, action_input_args)
        print result
      
      else:
        Usage('Unknown Action in Category: %s: %s' % (action_args[1], action_args[2]))
    
    else:
      Usage('Unknown Category: %s' % action_args[1])
  
  
  # Else, Initialize a directory to be a SchemaMan location
  elif action == 'init':
    if len(action_args) == 0:
      Usage('"init" action requires 1 argument: directory to store schema definition inside of')
    elif not os.path.isdir(action_args[0]):
      Usage('"init" action requires arguments: %s: Is not a directory' % action_args[0])
    
    schema_dir = action_args[0]
    
    Log('Initializing Schema Definition Directory: %s' % schema_dir)
    
    # Collect the initialization data from the user
    data = utility.interactive_input.CollectInitializationDataFromInput()
    
    schema_path = '%s/%s.yaml' % (schema_dir, data['alias'])
    
    # Check to see if we havent already created this schema definition.  We don't allow init twice, let them clean it up.
    if os.path.exists(schema_path):
      Error('The file you requested to initialize already exists, choose another Schema Alias: %s' % schema_path)
  
    # Create the location for our schema record paths.  This is the specific data source record schema, whereas the schema_path is the definition for the data set
    schema_record_path = '%s/schema/%s.yaml' % (schema_dir, data['alias'])
    
    
    # We need to create this directory, if it doesnt exist
    schema_record_path_dir = os.path.dirname(schema_record_path)
    if not os.path.isdir(schema_record_path_dir):
      os.makedirs(schema_record_path_dir, mode=MODE_DIRECTORY)
    
    
    # If we dont have this file yet, create it, so we can write into it
    if not os.path.isfile(schema_record_path):
      with open(schema_record_path, 'w') as fp:
        # Write an empty dictionary for YAML
        fp.write('{}\n')
    
    
    # Format the data into the expandable schema format (we accept lots more data, but on init we just want 1 set of data)
    schema_data = {
      'alias': data['alias'],
      'name': data['name'],
      'owner_user': data['owner_user'],
      'owner_group': data['owner_group'],
      'datasource': {
        'database': data['database_name'],
        'user': data['database_user'],
        'password_path': data['database_password_path'],
        'master_server_id': 1,
        'servers': [
          {
            'id': 1,
            'host': data['database_host'],
            'port': data['database_port'],
            'type': data['database_type'],
          },
        ],
      },
      'schema_paths': [schema_record_path],
      'value_type_path': 'data/schema/value_types/standard.yaml',
    }
    
    SaveYaml(schema_path, schema_data)
    
    Log('Initialized new schema path: %s' % schema_path)
  
  
  # Else, if Action prefix is Schema
  elif action == 'schema':
    # Ensure there are sub-actions, as they are always required
    if len(action_args) == 0:
      Usage('"schema" action requires arguments: create, export, extract, migrate, update')
    
    
    elif action_args[0] == 'create':
      connection_data = datasource.LoadConnectionSpec(action_args[1])
      
      result = datasource.CreateSchema(connection_data)
    
    
    # Export the current DB schema to a specified data source
    elif action_args[0] == 'export':
      if len(action_args) == 3:
        Usage('"schema export" action requires arguments: <path to connection spec> <path to export data to>')
      
      connection_data = datasource.LoadConnectionSpec(action_args[1])
      
      target_path = action_args[2]
      
      if not os.path.isdir(os.path.dirname(target_path)):
        Usage('Path specified does not have a valid directory: %s' % target_path)
      
      result = datasource.ExportSchema(connection_data, target_path)
    
    
    # Extract is the opposite of "update", and will get our DB schema and put it into our files where we "update" from
    elif action_args[0] == 'extract':
      if len(action_args) == 1:
        Usage('"schema extract" action requires arguments: <path to connection spec>')
      
      connection_data = datasource.LoadConnectionSpec(action_args[1])
      
      result = datasource.ExtractSchema(connection_data)
      
      print 'Extract Schema:'
      
      pprint.pprint(result)
      
      # Save the extracted schema to the last file in the connection data (which updates over the rest)
      #TODO(g): We should load all the previous files, and then only update things that are already in the current files, and save them, and then add any new things to the last file.
      output_path = connection_data['schema_paths'][-1]
      
      SaveYaml(output_path, result)
    
    
    elif action_args[0] == 'migrate':
      # Export from one, and import to another, in one step
      source_result = datasource.ExportSchema()
      target_result = datasource.UpdateSchema(source_result)
    
    
    # Update the database based on our schema spec files
    elif action_args[0] == 'update':
      connection_data = datasource.LoadConnectionSpec(action_args[1])
      
      result = datasource.UpdateSchema(connection_data)
    
    
    # ERROR
    else:
      Usage('Unknown Schema action: %s' % action)
  
  
  # Else, if Action prefix is Data
  elif action == 'data':
    if len(action_args) == 0:
      Usage('"data" action requires arguments: export, import')
    elif action_args[0] == 'export':
      result = datasource.ExportData()
    
    elif action_args[0] == 'import':
      result = datasource.ImportData()
    
    # ERROR
    else:
      Usage('Unknown Data action: %s' % action)
  
  # Put
  elif action == 'put':
    result = datasource.Put()
  
  # Get
  elif action == 'get':
    result = datasource.Get()
  
  # Filter
  elif action == 'filter':
    result = datasource.Filter()
  
  # Delete
  elif action == 'delete':
    result = datasource.Delete()
  
  # ERROR
  else:
    Usage('Unknown action: %s' % action)


def Main(args=None):
  if not args:
    args = []

  
  long_options = ['dir=', 'verbose', 'help', 'yes']
  
  try:
    (options, args) = getopt.getopt(args, '?hvyd:', long_options)
  except getopt.GetoptError, e:
    Usage(e)
  
  # Dictionary of command options, with defaults
  command_options = {}
  command_options['verbose'] = False
  command_options['always_yes'] = False
  
  
  # Process out CLI options
  for (option, value) in options:
    # Help
    if option in ('-h', '-?', '--help'):
      Usage()
    
    # Verbose output information
    elif option in ('-v', '--verbose'):
      command_options['verbose'] = True
    
    # Always answer Yes to prompts
    elif option in ('-y', '--yes'):
      command_options['always_yes'] = True
    
    # Invalid option
    else:
      Usage('Unknown option: %s' % option)


  # Store the command options for our logging
  utility.log.RUN_OPTIONS = command_options
  
  
  # Ensure we at least have one spec file
  if len(args) < 1:
    Usage('No action specified')
  

  #try:
  if 1:
    ProcessAction(args[0], args[1:], command_options)
    pass
  
  #NOTE(g): Catch all exceptions, and return in properly formatted output
  #TODO(g): Implement stack trace in Exception handling so we dont lose where this
  #   exception came from, and can then wrap all runs and still get useful
  #   debugging information
  #except Exception, e:
  else:
    Error({'exception':str(e)}, command_options)


if __name__ == '__main__':
  #NOTE(g): Fixing the path here.  If you're calling this as a module, you have to 
  #   fix the utility/handlers module import problem yourself.
  sys.path.append(os.path.dirname(sys.argv[0]))
  
  Main(sys.argv[1:])
