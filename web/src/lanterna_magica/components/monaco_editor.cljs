(ns lanterna-magica.components.monaco-editor
  (:require [reagent.core :as r]
            ["@monaco-editor/react" :as monaco-pkg]))

(def ^:private monaco-react (r/adapt-react-class (.-Editor monaco-pkg)))

(def ^:private monaco-diff-react
  (r/adapt-react-class (.-DiffEditor monaco-pkg)))

(defn monaco-editor
  "Monaco editor wrapper. Uses defaultValue to avoid cursor-jump on re-frame round-trips.
   Props:
     :value       Initial value (only read on mount — editor owns state after that)
     :language    Editor language mode (default \"json\"); can be changed dynamically
     :on-change   Called with new string value on each edit
     :height      CSS height string (default \"300px\")
     :read-only   Boolean (default false)"
  [{:keys [value language on-change height read-only]
    :or   {language "json" height "300px" read-only false}}]
  [monaco-react
   {:default-value         (or value "")
    :language              language
    :theme                 "vs-dark"
    :height                height
    :loading               (r/as-element [:span.text-tn-fg-dim.text-sm "Loading editor..."])
    :on-change             on-change
    :options               {:minimap              {:enabled false}
                            :scrollBeyondLastLine false
                            :fontSize             13
                            :tabSize              2
                            :readOnly             read-only
                            :wordWrap             "on"
                            :formatOnPaste        true
                            :formatOnType         true}}])

(defn monaco-diff-editor
  "Read-only diff editor. original = left (body), modified = right (projected)."
  [{:keys [original modified height]
    :or   {height "400px"}}]
  [monaco-diff-react
   {:original          original
    :modified          modified
    :language          "json"
    :theme             "vs-dark"
    :height            height
    :options           {:readOnly             true
                        :renderSideBySide     true
                        :minimap              {:enabled false}
                        :scrollBeyondLastLine false
                        :fontSize             13}}])
